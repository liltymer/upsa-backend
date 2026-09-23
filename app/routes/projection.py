from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.enrollment import Enrollment
from app.schemas.projection import SimulateRequest
from app.services.enrollments import get_enrollment
from app.services.projection_engine import simulate_future_cgpa, calculate_target_grade

router = APIRouter(prefix="/projection", tags=["GPA Projection"])


@router.post("/simulate")
def simulate_projection(
    payload: SimulateRequest,
    db: Session = Depends(get_db),
    enrollment: Enrollment = Depends(get_enrollment),
):
    """
    Hypothetical future courses with expected grade points → the programme's
    projected CGPA. Nothing is saved.
    """
    courses = [course.model_dump() for course in payload.projected_courses]
    return {
        "enrollment_id": enrollment.id,
        "projected_courses": len(courses),
        **simulate_future_cgpa(db, enrollment, courses),
        "note": "This is a simulation only. No data has been saved.",
    }


@router.get("/target")
def target_grade_calculator(
    target_cgpa: float = Query(ge=0.0, le=4.0),
    remaining_credits: int = Query(gt=0, le=200),
    db: Session = Depends(get_db),
    enrollment: Enrollment = Depends(get_enrollment),
):
    """
    Example: GET /projection/target?target_cgpa=3.6&remaining_credits=30
    """
    if target_cgpa <= 0:
        raise HTTPException(status_code=400, detail="Target CGPA must be greater than 0.")
    return {
        "enrollment_id": enrollment.id,
        **calculate_target_grade(db, enrollment, target_cgpa, remaining_credits),
    }
