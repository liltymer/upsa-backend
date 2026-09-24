"""
Courses to pre-fill when a student adds a semester.

Two sources, merged:
- the programme's course list (from UPSA's published timetables, or added by an admin)
- what other students on the same programme recorded for that level and semester,
  once at least LEARN_THRESHOLD different students entered the course.

Only course codes, titles and credit hours are shared between students, never grades
or who entered them.
"""
from collections import Counter, defaultdict

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.course import Course, CourseOffering
from app.models.enrollment import Enrollment
from app.models.result import Result
from app.utils.grading import level_for_academic_year

LEARN_THRESHOLD = 2


def learned_courses(db: Session, programme: str, level: int, semester: int, min_students: int = LEARN_THRESHOLD) -> dict[str, dict]:
    """Courses students on this programme recorded for a level and semester, with how many students did."""
    rows = (
        db.query(Result, Enrollment)
        .join(Enrollment, Result.enrollment_id == Enrollment.id)
        .filter(func.lower(Enrollment.programme) == programme.lower(), Result.semester == semester)
        .all()
    )
    seen = defaultdict(lambda: {"students": set(), "names": Counter(), "credits": Counter()})
    for result, enrollment in rows:
        if level_for_academic_year(enrollment.entry_level, enrollment.start_academic_year, result.academic_year) != level:
            continue
        entry = seen[result.course_code]
        entry["students"].add(result.student_id)
        entry["names"][result.course_name] += 1
        entry["credits"][result.credit_hours] += 1
    return {
        code: {
            "name": e["names"].most_common(1)[0][0],
            "credit_hours": e["credits"].most_common(1)[0][0],
            "students": len(e["students"]),
        }
        for code, e in seen.items()
        if len(e["students"]) >= min_students
    }


def suggest_courses(db: Session, enrollment: Enrollment, academic_year: str, semester: int) -> dict:
    level = level_for_academic_year(enrollment.entry_level, enrollment.start_academic_year, academic_year)
    programme = enrollment.programme

    offerings = (
        db.query(CourseOffering)
        .filter(
            func.lower(CourseOffering.programme) == programme.lower(),
            CourseOffering.level == level,
            CourseOffering.semester == semester,
        )
        .all()
    )
    hidden = {o.course_code for o in offerings if o.hidden}
    listed = {o.course_code for o in offerings if not o.hidden}
    learned = {code: v for code, v in learned_courses(db, programme, level, semester).items() if code not in hidden}

    codes = listed | set(learned)
    catalogue = {c.code: c for c in db.query(Course).filter(Course.code.in_(codes)).all()} if codes else {}

    mine = db.query(Result.course_code, Result.academic_year, Result.semester).filter(
        Result.enrollment_id == enrollment.id
    ).all()
    this_semester = {code for code, year, sem in mine if year == academic_year and sem == semester}
    recorded_before = {code for code, _, _ in mine} - this_semester

    courses = []
    for code in codes - this_semester:
        course = catalogue.get(code)
        from_students = learned.get(code)
        if not course and not from_students:
            continue
        courses.append({
            "course_code": code,
            "course_name": from_students["name"] if from_students else course.name,
            "credit_hours": from_students["credit_hours"] if from_students else course.credit_hours,
            # Timetables do not print credits, so they are a best guess until students or an admin confirm them
            "credits_confirmed": bool(from_students) or (course is not None and course.source != "timetable"),
            "source": "both" if code in listed and from_students else ("list" if code in listed else "students"),
            "recorded_before": code in recorded_before,
        })
    courses.sort(key=lambda c: (c["recorded_before"], c["course_code"]))

    return {
        "programme": programme,
        "level": level,
        "academic_year": academic_year,
        "semester": semester,
        "courses": courses,
    }
