from sqlalchemy.orm import Session

from app.models.enrollment import Enrollment
from app.models.result import Result
from app.utils.gpa import semester_summaries, totals
from app.utils.grading import (
    get_classification,
    level_for_academic_year,
    truncate_gpa,
)

SEMESTER_NAMES = {1: "First Semester", 2: "Second Semester"}


def generate_transcript(db: Session, enrollment: Enrollment) -> dict:
    """
    Transcript for ONE programme, grouped by semester in chronological order
    with the same per-semester figures as the UPSA transcript.
    """
    student = enrollment.student
    results = (
        db.query(Result)
        .filter(Result.enrollment_id == enrollment.id)
        .order_by(Result.academic_year, Result.semester, Result.course_code)
        .all()
    )

    semesters = []
    for s in semester_summaries(results):
        semesters.append({
            "academic_year": s["academic_year"],
            "semester": s["semester"],
            "title": f"{s['academic_year']} Academic Year - {SEMESTER_NAMES[s['semester']]}",
            "level": level_for_academic_year(
                enrollment.entry_level, enrollment.start_academic_year, s["academic_year"]
            ),
            "courses": [
                {
                    "course_code": r.course_code,
                    "course_title": r.course_name,
                    "credits": r.credit_hours,
                    "grade": r.grade,
                    "grade_point": r.grade_point,
                    "grade_value": r.grade_point * r.credit_hours,
                }
                for r in s["results"]
            ],
            "total_credits": s["total_credits"],
            "total_grade_points": s["total_grade_points"],
            "semester_gpa": s["gpa"],
            "cumulative_credits": s["cumulative_credits"],
            "cumulative_grade_points": s["cumulative_grade_points"],
            "cgpa": s["cgpa"],
        })

    points, credits = totals(results)
    cgpa = truncate_gpa(points, credits)
    last_year = semesters[-1]["academic_year"] if semesters else enrollment.start_academic_year

    return {
        "enrollment_id": enrollment.id,
        "student_name": student.name,
        "index_number": enrollment.index_number,
        "programme": enrollment.programme,
        "award_type": enrollment.award_type,
        "status": enrollment.status,
        "level": enrollment.current_level,
        "academic_year": enrollment.start_academic_year,
        "period": f"{enrollment.start_academic_year} to {last_year}",
        "transcript": semesters,
        "total_credits": credits,
        "total_grade_points": points,
        "cgpa": cgpa,
        "classification": get_classification(cgpa, enrollment.award_type) if results else None,
    }
