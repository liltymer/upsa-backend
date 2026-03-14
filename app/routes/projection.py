from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.services.auth import get_current_user
from app.models.student import Student
from app.services.projection_engine import simulate_future_cgpa, calculate_target_grade
from app.schemas.projection import ProjectedCourse

router = APIRouter(prefix="/projection", tags=["GPA Projection"])


# ===============================
# SIMULATE FUTURE CGPA
# ===============================

@router.post("/simulate")
def simulate_projection(
    projected_courses: List[ProjectedCourse],
    db: Session = Depends(get_db),
    current_user: Student = Depends(get_current_user)
):
    """
    Student inputs hypothetical future courses with expected
    grade points. Returns what their CGPA would become.
    Does NOT save anything to the database.
    """

    if not projected_courses:
        raise HTTPException(
            status_code=400,
            detail="Provide at least one projected course."
        )

    courses = [course.dict() for course in projected_courses]

    projected_cgpa = simulate_future_cgpa(
        db,
        current_user.id,
        courses
    )

    return {
        "student": current_user.name,
        "projected_courses": len(courses),
        "projected_cgpa": projected_cgpa,
        "note": "This is a simulation only. No data has been saved."
    }


# ===============================
# TARGET GRADE CALCULATOR
# ===============================

@router.get("/target")
def target_grade_calculator(
    target_cgpa: float,
    remaining_credits: int,
    db: Session = Depends(get_db),
    current_user: Student = Depends(get_current_user)
):
    """
    Reverse projection — tells the student exactly what grade
    they need to achieve their target CGPA given how many
    credits they have left.

    Example: GET /projection/target?target_cgpa=3.6&remaining_credits=30
    """

    if not (0.0 <= target_cgpa <= 4.0):
        raise HTTPException(
            status_code=400,
            detail="Target CGPA must be between 0.0 and 4.0"
        )

    if remaining_credits <= 0:
        raise HTTPException(
            status_code=400,
            detail="Remaining credits must be greater than 0"
        )

    result = calculate_target_grade(
        db,
        current_user.id,
        target_cgpa,
        remaining_credits
    )

    return {
        "student": current_user.name,
        **result
    }