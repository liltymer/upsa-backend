from sqlalchemy.orm import Session

from app.models.enrollment import Enrollment
from app.models.result import Result
from app.utils.gpa import totals
from app.utils.grading import get_classification, truncate_gpa


def _current_totals(db: Session, enrollment_id: int) -> tuple[float, int]:
    return totals(db.query(Result).filter(Result.enrollment_id == enrollment_id).all())


def simulate_future_cgpa(db: Session, enrollment: Enrollment, projected_courses: list[dict]) -> dict:
    """
    What the programme's CGPA would become with some hypothetical future courses.
    Does NOT write to the database.
    """
    points, credits = _current_totals(db, enrollment.id)
    current_cgpa = truncate_gpa(points, credits)

    for course in projected_courses:
        points += course["grade_point"] * course["credit_hours"]
        credits += course["credit_hours"]

    projected = truncate_gpa(points, credits)
    return {
        "current_cgpa": current_cgpa,
        "projected_cgpa": projected,
        "projected_classification": get_classification(projected, enrollment.award_type),
        "change": round(projected - current_cgpa, 2),
    }


def calculate_target_grade(
    db: Session,
    enrollment: Enrollment,
    target_cgpa: float,
    remaining_credits: int
) -> dict:
    """
    Reverse projection: the average grade point needed over the remaining
    credits of this programme to reach a target CGPA.
    """
    current_points, current_credits = _current_totals(db, enrollment.id)
    total_credits = current_credits + remaining_credits
    current_cgpa = truncate_gpa(current_points, current_credits)

    points_needed = target_cgpa * total_credits - current_points
    required = round(points_needed / remaining_credits, 2)

    if required > 4.0:
        max_possible = truncate_gpa(current_points + 4.0 * remaining_credits, total_credits)
        achievable = False
        message = (
            f"Target of {target_cgpa} is not achievable with {remaining_credits} credits remaining. "
            f"Maximum possible CGPA is {max_possible:.2f}."
        )
        required_grade_point = None
        required_grade = None
    elif required <= 0.0:
        achievable = True
        message = f"You have already exceeded a CGPA of {target_cgpa}. Your current CGPA is {current_cgpa:.2f}."
        required_grade_point = 0.0
        required_grade = "F"
    else:
        achievable = True
        required_grade_point = required
        required_grade = _grade_point_to_grade(required)
        message = (
            f"To reach a CGPA of {target_cgpa}, you need an average grade of {required_grade} "
            f"({required:.2f}) across your remaining {remaining_credits} credits."
        )

    return {
        "current_cgpa": current_cgpa,
        "current_credits_earned": current_credits,
        "target_cgpa": target_cgpa,
        "target_classification": get_classification(target_cgpa, enrollment.award_type),
        "remaining_credits": remaining_credits,
        "required_grade_point_average": required_grade_point,
        "required_grade": required_grade,
        "achievable": achievable,
        "message": message,
    }


def _grade_point_to_grade(gp: float) -> str:
    """The lowest UPSA grade whose grade point meets the required average."""
    for grade, point in [("D", 0.5), ("C-", 1.0), ("C", 1.5), ("C+", 2.0),
                         ("B-", 2.5), ("B", 3.0), ("B+", 3.5), ("A", 4.0)]:
        if gp <= point:
            return grade
    return "A"
