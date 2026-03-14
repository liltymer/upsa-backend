from sqlalchemy.orm import Session
from app.models.result import Result
from app.models.course import Course

GRADE_POINTS = {
    "A": 4.0,
    "B+": 3.5,
    "B": 3.0,
    "C+": 2.5,
    "C": 2.0,
    "D": 1.0,
    "F": 0.0,
}

def score_to_grade(score: float):
    if score >= 80:
        return "A"
    elif score >= 75:
        return "B+"
    elif score >= 70:
        return "B"
    elif score >= 65:
        return "C+"
    elif score >= 60:
        return "C"
    elif score >= 50:
        return "D"
    else:
        return "F"

def calculate_gpa(student_id: int, db: Session):

    results = db.query(Result).filter(Result.student_id == student_id).all()

    total_points = 0
    total_credits = 0

    for r in results:
        course = db.query(Course).filter(Course.id == r.course_id).first()

        grade = score_to_grade(r.score)
        points = GRADE_POINTS[grade]

        total_points += points * course.credit_hours
        total_credits += course.credit_hours

    if total_credits == 0:
        return 0

    return round(total_points / total_credits, 2)
