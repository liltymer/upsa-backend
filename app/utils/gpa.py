from sqlalchemy.orm import Session
from app.models.result import Result


def calculate_semester_gpa(db: Session, student_id: int, year: int, semester: int) -> float:
    """
    Calculate GPA for a specific semester.
    Reads grade_point and credit_hours directly from Result.
    No join needed — course details live on the Result row.
    """
    results = (
        db.query(Result)
        .filter(
            Result.student_id == student_id,
            Result.year == year,
            Result.semester == semester
        )
        .all()
    )

    total_points = 0.0
    total_credits = 0

    for r in results:
        total_points += r.grade_point * r.credit_hours
        total_credits += r.credit_hours

    if total_credits == 0:
        return 0.0

    return round(total_points / total_credits, 2)


def calculate_cgpa(db: Session, student_id: int) -> float:
    """
    Calculate cumulative GPA across all semesters.
    """
    results = (
        db.query(Result)
        .filter(Result.student_id == student_id)
        .all()
    )

    total_points = 0.0
    total_credits = 0

    for r in results:
        total_points += r.grade_point * r.credit_hours
        total_credits += r.credit_hours

    if total_credits == 0:
        return 0.0

    return round(total_points / total_credits, 2)


def get_gpa_history(db: Session, student_id: int) -> list:
    """
    Returns GPA for every semester the student has results in,
    sorted chronologically.
    """
    semesters = (
        db.query(Result.year, Result.semester)
        .filter(Result.student_id == student_id)
        .distinct()
        .all()
    )

    history = []

    for year, semester in semesters:
        gpa = calculate_semester_gpa(db, student_id, year, semester)
        history.append({
            "year": year,
            "semester": semester,
            "gpa": gpa
        })

    return sorted(history, key=lambda x: (x["year"], x["semester"]))





