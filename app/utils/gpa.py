from collections import defaultdict

from sqlalchemy.orm import Session

from app.models.result import Result
from app.utils.grading import truncate_gpa


def _results(db: Session, enrollment_id: int) -> list[Result]:
    return db.query(Result).filter(Result.enrollment_id == enrollment_id).all()


def totals(results) -> tuple[float, int]:
    """(total grade value, total credits) for a list of results."""
    points = sum(r.grade_point * r.credit_hours for r in results)
    credits = sum(r.credit_hours for r in results)
    return points, credits


def calculate_semester_gpa(db: Session, enrollment_id: int, academic_year: str, semester: int) -> float:
    """GPA for one semester of one programme."""
    results = (
        db.query(Result)
        .filter(
            Result.enrollment_id == enrollment_id,
            Result.academic_year == academic_year,
            Result.semester == semester,
        )
        .all()
    )
    return truncate_gpa(*totals(results))


def calculate_cgpa(db: Session, enrollment_id: int) -> float:
    """Cumulative GPA across every semester of one programme."""
    return truncate_gpa(*totals(_results(db, enrollment_id)))


def semester_summaries(results) -> list[dict]:
    """
    Groups results by semester in chronological order with the figures
    printed on a UPSA transcript: TCR, TGP, GPA and the running CGPA.
    """
    grouped = defaultdict(list)
    for r in results:
        grouped[(r.academic_year, r.semester)].append(r)

    summaries = []
    cum_points, cum_credits = 0.0, 0
    for (academic_year, semester), rows in sorted(grouped.items()):
        points, credits = totals(rows)
        cum_points += points
        cum_credits += credits
        summaries.append({
            "academic_year": academic_year,
            "semester": semester,
            "results": rows,
            "total_credits": credits,
            "total_grade_points": points,
            "gpa": truncate_gpa(points, credits),
            "cumulative_credits": cum_credits,
            "cumulative_grade_points": cum_points,
            "cgpa": truncate_gpa(cum_points, cum_credits),
        })
    return summaries


def get_gpa_history(db: Session, enrollment_id: int) -> list[dict]:
    """GPA for every semester of a programme, sorted chronologically."""
    return [
        {
            "academic_year": s["academic_year"],
            "semester": s["semester"],
            "gpa": s["gpa"],
            "cgpa": s["cgpa"],
        }
        for s in semester_summaries(_results(db, enrollment_id))
    ]
