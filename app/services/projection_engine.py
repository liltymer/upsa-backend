from sqlalchemy.orm import Session
from app.models.result import Result
from app.models.course import Course


def simulate_future_cgpa(db: Session, student_id: int, projected_courses: list) -> float:
    """
    Simulates what a student's CGPA would be if they achieved
    certain grade points in future courses.
    Takes existing real results + hypothetical future courses.
    Does NOT write to the database.
    """

    results = (
        db.query(Result)
        .join(Course)
        .filter(Result.student_id == student_id)
        .all()
    )

    total_points = 0.0
    total_credits = 0

    for r in results:
        credit = r.course.credit_hours
        total_points += r.grade_point * credit
        total_credits += credit

    for course in projected_courses:
        credit = course["credit_hours"]
        grade_point = course["grade_point"]
        total_points += grade_point * credit
        total_credits += credit

    if total_credits == 0:
        return 0.0

    return round(total_points / total_credits, 2)


def calculate_target_grade(
    db: Session,
    student_id: int,
    target_cgpa: float,
    remaining_credits: int
) -> dict:
    """
    Reverse projection — answers:
    'What grade point do I need per credit in remaining courses
    to reach my target CGPA?'

    Returns the required grade point average and what UPSA
    grade that corresponds to.
    """

    # Validate target
    if not (0.0 <= target_cgpa <= 4.0):
        return {
            "error": "Target CGPA must be between 0.0 and 4.0"
        }

    if remaining_credits <= 0:
        return {
            "error": "Remaining credits must be greater than 0"
        }

    # Get current totals from real results
    results = (
        db.query(Result)
        .join(Course)
        .filter(Result.student_id == student_id)
        .all()
    )

    current_points = 0.0
    current_credits = 0

    for r in results:
        credit = r.course.credit_hours
        current_points += r.grade_point * credit
        current_credits += credit

    total_credits = current_credits + remaining_credits

    # Required total points to hit target
    required_total_points = target_cgpa * total_credits

    # Points still needed from remaining courses
    points_needed = required_total_points - current_points

    # Average grade point needed per credit
    required_grade_point = points_needed / remaining_credits

    required_grade_point = round(required_grade_point, 2)

    # Current CGPA
    current_cgpa = (
        round(current_points / current_credits, 2)
        if current_credits > 0 else 0.0
    )

    # Determine if target is achievable
    if required_grade_point > 4.0:
        achievable = False
        message = (
            f"Target of {target_cgpa} is not achievable with "
            f"{remaining_credits} credits remaining. "
            f"Maximum possible CGPA is {round((current_points + 4.0 * remaining_credits) / total_credits, 2)}."
        )
        required_grade_point = None
        required_grade = None

    elif required_grade_point < 0.0:
        achievable = True
        message = (
            f"You have already exceeded a CGPA of {target_cgpa}. "
            f"Your current CGPA is {current_cgpa}."
        )
        required_grade_point = 0.0
        required_grade = "F"

    else:
        achievable = True
        required_grade = _grade_point_to_grade(required_grade_point)
        message = (
            f"To reach a CGPA of {target_cgpa}, you need an average "
            f"grade of {required_grade} ({required_grade_point}) "
            f"across your remaining {remaining_credits} credits."
        )

    return {
        "current_cgpa": current_cgpa,
        "current_credits_earned": current_credits,
        "target_cgpa": target_cgpa,
        "remaining_credits": remaining_credits,
        "required_grade_point_average": required_grade_point,
        "required_grade": required_grade,
        "achievable": achievable,
        "message": message
    }


def _grade_point_to_grade(gp: float) -> str:
    """
    Maps a required grade point average back to the
    closest UPSA grade label.
    """
    if gp >= 4.0:
        return "A"
    elif gp >= 3.5:
        return "B+"
    elif gp >= 3.0:
        return "B"
    elif gp >= 2.5:
        return "B-"
    elif gp >= 2.0:
        return "C+"
    elif gp >= 1.5:
        return "C"
    elif gp >= 1.0:
        return "C-"
    elif gp >= 0.5:
        return "D"
    else:
        return "F"