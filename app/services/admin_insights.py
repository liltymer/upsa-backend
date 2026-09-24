"""
What an admin needs to notice: activity over time, things that need attention,
the hardest courses and the top-up pipeline. Counts only; courses are shown only
when enough students took them that nobody can be singled out.
"""
import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.announcement import Announcement
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.result import Result
from app.models.student import Student
from app.utils.grading import PROBATION_THRESHOLD, truncate_gpa

MIN_STUDENTS_FOR_COURSE_STATS = 5
WEEKS = 8


def _aware(value):
    # SQLite (tests, local) returns naive UTC; Postgres returns aware values
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _activity(db: Session, now: datetime) -> dict:
    students = [(_aware(c), _aware(seen)) for c, seen in db.query(Student.created_at, Student.last_login_at).filter(Student.role == "student")]
    results = [_aware(c) for (c,) in db.query(Result.created_at)]

    def since(values, days):
        cutoff = now - timedelta(days=days)
        return sum(1 for v in values if v and v >= cutoff)

    start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(weeks=WEEKS - 1)
    weeks = []
    for i in range(WEEKS):
        a, b = start + timedelta(weeks=i), start + timedelta(weeks=i + 1)
        weeks.append({
            "week_start": a.date().isoformat(),
            "signups": sum(1 for c, _ in students if c and a <= c < b),
            "results": sum(1 for c in results if c and a <= c < b),
        })

    return {
        "signups_7d": since([c for c, _ in students], 7),
        "signups_30d": since([c for c, _ in students], 30),
        "results_7d": since(results, 7),
        "results_30d": since(results, 30),
        "active_7d": since([s for _, s in students], 7),
        "active_30d": since([s for _, s in students], 30),
        "weekly": weeks,
    }


def _hardest_courses(db: Session) -> list[dict]:
    rows = db.query(Result.course_code, Result.course_name, Result.student_id, Result.grade, Result.grade_point, Result.credit_hours).all()
    by_code = defaultdict(lambda: {"students": set(), "names": defaultdict(int), "fails": 0, "attempts": 0, "points": 0.0, "credits": 0})
    for code, name, sid, grade, gp, cr in rows:
        c = by_code[code]
        c["students"].add(sid)
        c["names"][name] += 1
        c["attempts"] += 1
        c["fails"] += grade in ("D", "F")
        c["points"] += gp * cr
        c["credits"] += cr
    courses = [
        {
            "course_code": code,
            "course_name": max(c["names"], key=c["names"].get),
            "students": len(c["students"]),
            "fail_rate": round(c["fails"] / c["attempts"], 2),
            "average_grade_point": truncate_gpa(c["points"], c["credits"]),
        }
        for code, c in by_code.items()
        if len(c["students"]) >= MIN_STUDENTS_FOR_COURSE_STATS
    ]
    courses.sort(key=lambda c: (-c["fail_rate"], c["average_grade_point"]))
    return courses[:5]


def _attention(db: Session) -> list[dict]:
    items = []

    def add(level, title, body, link=None, count=None):
        items.append({"level": level, "title": title, "body": body, "link": link, "count": count})

    if not os.getenv("RESEND_API_KEY", "").strip():
        add("critical", "Password reset emails are off",
            "RESEND_API_KEY is not set on the server, so students who forget their password cannot reset it.")
    elif "resend.dev" in os.getenv("EMAIL_FROM", "onboarding@resend.dev"):
        add("critical", "Password reset emails only reach you",
            "EMAIL_FROM still uses Resend's test sender, which only delivers to the Resend account owner. "
            "Verify your domain in Resend and set EMAIL_FROM on Render.")

    review = db.query(Enrollment).filter(Enrollment.needs_review.is_(True)).count()
    if review:
        add("warning", "Programme records waiting for students to confirm",
            "Created when diploma and degree results were separated. The students are asked to confirm them on their Profile.",
            count=review)

    points = func.sum(Result.grade_point * Result.credit_hours)
    credits = func.sum(Result.credit_hours)
    probation = sum(
        1 for p, c in db.query(points, credits).join(Enrollment, Result.enrollment_id == Enrollment.id)
        .filter(Enrollment.is_current.is_(True)).group_by(Result.enrollment_id)
        if c and truncate_gpa(p, c) < PROBATION_THRESHOLD
    )
    if probation:
        add("warning", "Students on probation", "Their CGPA is below 1.00 (handbook 4.19). Consider an announcement about academic support.",
            link="/admin/announcements", count=probation)

    known = {c for (c,) in db.query(Course.code)}
    unknown = {c for (c,) in db.query(Result.course_code).distinct()} - known
    if unknown:
        add("info", "Course codes students typed that are not in the catalogue",
            "Check them in Courses. Real ones can be added so other students get them as suggestions.",
            link="/admin/courses", count=len(unknown))

    unconfirmed = db.query(Course).filter(Course.source == "timetable").count()
    if unconfirmed:
        add("info", "Courses with credits not yet confirmed",
            "Loaded from UPSA's timetables, which do not list credit hours. Edit a course to confirm its credits.",
            link="/admin/courses", count=unconfirmed)

    if not db.query(Announcement).filter(Announcement.is_active.is_(True)).count():
        add("info", "No announcement is showing", "Students see announcements on their dashboard. Post one for deadlines or exam changes.",
            link="/admin/announcements")
    return items


def _top_up_pipeline(db: Session) -> dict:
    per_student = defaultdict(set)
    for sid, award in db.query(Enrollment.student_id, Enrollment.award_type).join(
        Student, Student.id == Enrollment.student_id
    ).filter(Student.role == "student"):
        per_student[sid].add(award)
    diploma_only = {sid for sid, awards in per_student.items() if awards == {"diploma"}}

    # A diploma is four semesters: count each student's distinct semesters in one pass
    terms = defaultdict(set)
    if diploma_only:
        for sid, year, sem in db.query(Result.student_id, Result.academic_year, Result.semester).filter(
            Result.student_id.in_(diploma_only)
        ).distinct():
            terms[sid].add((year, sem))
    finished = sum(1 for sid in diploma_only if len(terms[sid]) >= 4)
    return {
        "topped_up": sum(1 for awards in per_student.values() if {"diploma", "degree"} <= awards),
        "diploma_finished_not_topped_up": finished,
        "diploma_in_progress": len(diploma_only) - finished,
    }


def admin_insights(db: Session) -> dict:
    now = datetime.now(timezone.utc)
    return {
        "activity": _activity(db, now),
        "attention": _attention(db),
        "hardest_courses": _hardest_courses(db),
        "min_students_for_course_stats": MIN_STUDENTS_FOR_COURSE_STATS,
        "top_up": _top_up_pipeline(db),
    }
