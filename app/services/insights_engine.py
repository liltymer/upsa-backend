"""
Turns a programme's results into the picture a student needs to act on:
where they stand, what is pulling their CGPA down, where they are strongest,
how each subject area is going, and what to do next.
"""
import re
from collections import Counter, defaultdict
from typing import Optional

from sqlalchemy.orm import Session

from app.models.enrollment import Enrollment
from app.models.result import Result
from app.services.stage_engine import academic_stage
from app.utils.gpa import semester_summaries, totals
from app.utils.grading import (
    CLASSIFICATION_BANDS,
    MAX_LEVEL,
    VALID_GRADES,
    current_academic_year,
    get_classification,
    get_next_band,
    level_for_academic_year,
    parse_academic_year,
    truncate_gpa,
)

SEMESTER_NAMES = {1: "First Semester", 2: "Second Semester"}
TOP_N = 5


def _grade_for_average(gp: float) -> str:
    """Lowest UPSA grade whose point value meets the required average."""
    for grade, point in [("D", 0.5), ("C-", 1.0), ("C", 1.5), ("C+", 2.0),
                         ("B-", 2.5), ("B", 3.0), ("B+", 3.5), ("A", 4.0)]:
        if gp <= point + 1e-9:
            return grade
    return "A"


def _area_code(course_code: str) -> str:
    """Leading letters of a course code: DIPT052 -> DIPT, BIT301 -> BIT."""
    match = re.match(r"[A-Za-z]+", course_code.strip())
    return match.group(0).upper() if match else course_code.strip().upper()


# Friendly names for UPSA course-code prefixes. Students can rename any area.
DEFAULT_AREA_NAMES = {
    "DIPC": "Core business",
    "DIPT": "Information technology",
    "DIPL": "Law",
    "DIPA": "Accounting",
    "DIPM": "Marketing and management",
    "DIPP": "Public relations",
}


def area_label(code: str, custom: Optional[dict]) -> str:
    if custom and custom.get(code):
        return custom[code]
    return DEFAULT_AREA_NAMES.get(code, code)


def _cgpa_effect(r: Result, points: float, credits: int) -> float:
    """How much this course moved the CGPA: CGPA with it minus CGPA without it."""
    rest_credits = credits - r.credit_hours
    if rest_credits <= 0:
        return 0.0
    without = (points - r.grade_point * r.credit_hours) / rest_credits
    return round(points / credits - without, 2)


def _course(r: Result, enrollment: Enrollment, cgpa: float, points: float = 0.0, credits: int = 0) -> dict:
    return {
        "result_id": r.id,
        "course_code": r.course_code,
        "course_name": r.course_name,
        "credit_hours": r.credit_hours,
        "grade": r.grade,
        "grade_point": r.grade_point,
        "academic_year": r.academic_year,
        "semester": r.semester,
        "level": level_for_academic_year(enrollment.entry_level, enrollment.start_academic_year, r.academic_year),
        # How many grade points (x credits) this course sits below or above the CGPA
        "impact": round((r.grade_point - cgpa) * r.credit_hours, 2),
        # Plain version for students: negative means it lowered the CGPA by that much
        "cgpa_effect": _cgpa_effect(r, points, credits) if credits else 0.0,
    }


def estimate_remaining(enrollment: Enrollment, summaries: list[dict], credits_done: int) -> dict:
    """
    Estimated credits still to take on this programme: semesters left until the
    final level, multiplied by the student's average credits per semester.
    """
    award_levels = (MAX_LEVEL[enrollment.award_type] - enrollment.entry_level) // 100 + 1
    total_semesters = award_levels * 2
    done = len(summaries)
    remaining_semesters = max(total_semesters - done, 0)
    per_semester = round(credits_done / done) if done else 18
    return {
        "total_semesters": total_semesters,
        "semesters_done": done,
        "remaining_semesters": remaining_semesters,
        "average_credits_per_semester": per_semester,
        "remaining_credits": remaining_semesters * per_semester,
    }


def generate_insights(db: Session, enrollment: Enrollment, remaining_credits: Optional[int] = None) -> dict:
    results = (
        db.query(Result)
        .filter(Result.enrollment_id == enrollment.id)
        .order_by(Result.academic_year, Result.semester, Result.course_code)
        .all()
    )
    award = enrollment.award_type
    bands = CLASSIFICATION_BANDS[award]
    points, credits = totals(results)
    cgpa = truncate_gpa(points, credits)
    summaries = semester_summaries(results)
    has_results = bool(results)

    classification = get_classification(cgpa, award) if has_results else None
    next_band = get_next_band(cgpa, award) if has_results else None
    current_band = next((b for b in bands if cgpa >= b["min"]), bands[-1])

    # ---- trend ----
    history = [
        {
            "academic_year": s["academic_year"],
            "semester": s["semester"],
            "title": f"{s['academic_year']} {SEMESTER_NAMES[s['semester']]}",
            "gpa": s["gpa"],
            "cgpa": s["cgpa"],
            "credits": s["total_credits"],
        }
        for s in summaries
    ]
    latest = history[-1] if history else None
    previous = history[-2] if len(history) > 1 else None
    if latest and previous:
        direction = "improving" if latest["gpa"] > previous["gpa"] else "declining" if latest["gpa"] < previous["gpa"] else "steady"
    else:
        direction = None
    best_semester = max(history, key=lambda h: h["gpa"]) if history else None
    weakest_semester = min(history, key=lambda h: h["gpa"]) if history else None

    # ---- courses ----
    courses = [_course(r, enrollment, cgpa, points, credits) for r in results]
    pulling_down = sorted([c for c in courses if c["impact"] < 0], key=lambda c: (c["impact"], c["grade_point"]))[:TOP_N]
    strongest = sorted([c for c in courses if c["grade_point"] >= 3.5],
                       key=lambda c: (-c["grade_point"], -c["credit_hours"], c["course_code"]))[:TOP_N]

    # ---- subject areas (by course code prefix) ----
    grouped = defaultdict(list)
    for r in results:
        grouped[_area_code(r.course_code)].append(r)
    areas = []
    for code, rows in grouped.items():
        p, c = totals(rows)
        areas.append({
            "area": code,
            "label": area_label(code, enrollment.area_labels),
            "custom_label": bool(enrollment.area_labels and enrollment.area_labels.get(code)),
            "courses": len(rows),
            "credits": c,
            "gpa": truncate_gpa(p, c),
            "vs_cgpa": round(truncate_gpa(p, c) - cgpa, 2),
        })
    areas.sort(key=lambda a: (-a["credits"], a["area"]))

    # ---- grade spread ----
    counts = Counter(r.grade for r in results)
    grade_distribution = [{"grade": g, "count": counts.get(g, 0)} for g in VALID_GRADES]

    # ---- what is needed next ----
    estimate = estimate_remaining(enrollment, summaries, credits)
    remaining = remaining_credits if remaining_credits is not None else estimate["remaining_credits"]
    target = None
    if has_results and next_band and remaining > 0:
        needed = (next_band["min"] * (credits + remaining) - points) / remaining
        needed = round(needed, 2)
        target = {
            "target_class": next_band["label"],
            "target_cgpa": next_band["min"],
            "remaining_credits": remaining,
            "remaining_credits_estimated": remaining_credits is None,
            "required_average": needed if needed <= 4.0 else None,
            "required_grade": _grade_for_average(needed) if 0 < needed <= 4.0 else None,
            "achievable": needed <= 4.0,
            "max_possible_cgpa": truncate_gpa(points + 4.0 * remaining, credits + remaining),
        }

    actions = _actions(enrollment, cgpa, classification, next_band, target, latest, previous,
                       pulling_down, areas, summaries, estimate)
    stage = academic_stage(enrollment, points, credits, cgpa, classification, next_band, estimate, remaining)

    return {
        "enrollment_id": enrollment.id,
        "programme": enrollment.programme,
        "award_type": award,
        "has_results": has_results,
        "summary": {
            "cgpa": cgpa,
            "classification": classification,
            "band_min": current_band["min"],
            "band_max": next_band["min"] if next_band else 4.0,
            "next_class": next_band["label"] if next_band else None,
            "gap_to_next_class": round(next_band["min"] - cgpa, 2) if next_band else None,
            "credits_completed": credits,
            "courses_completed": len(results),
            "semesters_completed": len(summaries),
            "latest_gpa": latest["gpa"] if latest else None,
            "latest_title": latest["title"] if latest else None,
            "previous_gpa": previous["gpa"] if previous else None,
            "direction": direction,
            "best_semester": best_semester,
            "weakest_semester": weakest_semester,
        },
        "classification_bands": bands,
        "history": history,
        "pulling_down": pulling_down,
        "strongest": strongest,
        "areas": areas,
        "grade_distribution": grade_distribution,
        "target": target,
        "estimate": estimate,
        "actions": actions,
        "stage": stage,
    }


def _actions(enrollment, cgpa, classification, next_band, target, latest, previous,
             pulling_down, areas, summaries, estimate) -> list[dict]:
    """Up to three plain next steps, most important first."""
    actions = []

    if not summaries:
        return [{
            "kind": "start",
            "title": "Add your first results",
            "body": "Enter the courses and grades from your result slip to see your GPA, class and where to focus.",
            "link": "/results",
        }]

    # A finished programme: look back and help with what comes next
    # (a student who enters credits still to take is not finished: target is set then)
    if (estimate["remaining_semesters"] == 0 and target is None) or enrollment.status == "completed":
        return _finished_actions(enrollment, cgpa, classification, pulling_down, areas)

    if cgpa < 1.0:
        actions.append({
            "kind": "urgent",
            "title": "Speak to your academic advisor",
            "body": "Your CGPA is below 1.0, which is the probation threshold. Get advice on which courses to prioritise this semester.",
            "link": "/standing",
        })

    if target:
        if target["achievable"] and target["required_grade"]:
            actions.append({
                "kind": "target",
                "title": f"Aim for an average of {target['required_grade']} to reach {target['target_class']}",
                "body": f"You need about {target['required_average']:.2f} grade points per credit over your remaining "
                        f"{target['remaining_credits']} credits.",
                "link": "/planner",
            })
        elif not target["achievable"]:
            actions.append({
                "kind": "target",
                "title": f"Protect your {classification}",
                "body": f"{target['target_class']} is out of reach with {target['remaining_credits']} credits left "
                        f"(highest possible CGPA is {target['max_possible_cgpa']:.2f}). Keep your grades steady to hold your class.",
                "link": "/planner",
            })

    if latest and previous and latest["gpa"] < previous["gpa"]:
        actions.append({
            "kind": "trend",
            "title": "Your GPA dropped last semester",
            "body": f"{latest['title']} GPA was {latest['gpa']:.2f}, down from {previous['gpa']:.2f}. "
                    "Look at which courses fell and adjust how you prepare.",
            "link": "/gpa",
        })
    elif latest and latest["gpa"] < cgpa:
        actions.append({
            "kind": "trend",
            "title": "Your latest semester was below your CGPA",
            "body": f"{latest['title']} GPA ({latest['gpa']:.2f}) is below your CGPA ({cgpa:.2f}).",
            "link": "/gpa",
        })

    weak_areas = [a for a in areas if a["courses"] >= 2 and a["vs_cgpa"] <= -0.3]
    if weak_areas:
        weakest = min(weak_areas, key=lambda a: a["gpa"])
        actions.append({
            "kind": "area",
            "title": f"Give your {weakest['label']} courses extra attention",
            "body": f"Your {weakest['label']} courses ({weakest['area']}) average {weakest['gpa']:.2f}, below your CGPA of {cgpa:.2f}.",
            "link": "/results",
        })
    elif pulling_down:
        worst = pulling_down[0]
        actions.append({
            "kind": "course",
            "title": f"{worst['course_code']} cost you the most",
            "body": f"A {worst['grade']} in a {worst['credit_hours']} credit course. Similar courses later on deserve more preparation time.",
            "link": "/results",
        })

    # Remind students to keep their record current
    last_year = summaries[-1]["academic_year"]
    now = current_academic_year()
    semesters_left = estimate["remaining_semesters"] > 0
    if parse_academic_year(last_year) < parse_academic_year(now) and enrollment.status == "active" and semesters_left:
        actions.append({
            "kind": "update",
            "title": f"Add your {now} results",
            "body": "Your record stops at " + last_year + ". Add new results as they come out to keep your advice accurate.",
            "link": "/results",
        })

    return actions[:3]


def _finished_actions(enrollment, cgpa, classification, pulling_down, areas) -> list[dict]:
    """Reflective next steps once every semester of a programme is recorded."""
    actions = []
    others = [e for e in enrollment.student.enrollments if e.id != enrollment.id]
    award_word = "diploma" if enrollment.award_type == "diploma" else "degree"

    if enrollment.award_type == "diploma" and not any(e.award_type == "degree" for e in others):
        actions.append({
            "kind": "topup",
            "title": "Topping up to a degree?",
            "body": f"Add your degree from Profile. Your {award_word} and its {classification} stay in your history, "
                    "and the degree starts a fresh CGPA.",
            "link": "/profile",
        })

    weak_areas = [a for a in areas if a["courses"] >= 2 and a["vs_cgpa"] <= -0.3]
    if weak_areas:
        weakest = min(weak_areas, key=lambda a: a["gpa"])
        actions.append({
            "kind": "area",
            "title": f"Your weakest area was {weakest['label']}",
            "body": f"Those courses ({weakest['area']}) averaged {weakest['gpa']:.2f} against your CGPA of {cgpa:.2f}. "
                    "If your next programme has similar courses, give them extra time from the start.",
            "link": "/results",
        })
    elif pulling_down:
        worst = pulling_down[0]
        actions.append({
            "kind": "course",
            "title": f"{worst['course_name']} cost you the most",
            "body": f"A {worst['grade']} in a {worst['credit_hours']} credit course. Plan extra preparation for similar courses later.",
            "link": "/results",
        })

    actions.append({
        "kind": "start",
        "title": "Keep a copy of your transcript",
        "body": f"Download your unofficial {award_word} transcript as a PDF for your records.",
        "link": "/transcript",
    })
    return actions[:3]
