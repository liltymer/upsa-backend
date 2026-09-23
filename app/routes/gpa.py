from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.enrollment import Enrollment
from app.services.enrollments import get_enrollment
from app.utils.gpa import calculate_semester_gpa, calculate_cgpa, get_gpa_history
from app.utils.grading import get_classification

router = APIRouter(prefix="/gpa", tags=["GPA"])


@router.get("/semester")
def semester_gpa(
    academic_year: str,
    semester: int = Query(ge=1, le=2),
    db: Session = Depends(get_db),
    enrollment: Enrollment = Depends(get_enrollment),
):
    return {
        "enrollment_id": enrollment.id,
        "academic_year": academic_year,
        "semester": semester,
        "semester_gpa": calculate_semester_gpa(db, enrollment.id, academic_year, semester),
    }


@router.get("/cgpa")
def cgpa(
    db: Session = Depends(get_db),
    enrollment: Enrollment = Depends(get_enrollment),
):
    value = calculate_cgpa(db, enrollment.id)
    return {
        "enrollment_id": enrollment.id,
        "award_type": enrollment.award_type,
        "cgpa": value,
        "classification": get_classification(value, enrollment.award_type),
    }


@router.get("/history")
def gpa_history(
    db: Session = Depends(get_db),
    enrollment: Enrollment = Depends(get_enrollment),
):
    return {
        "enrollment_id": enrollment.id,
        "gpa_history": get_gpa_history(db, enrollment.id),
    }
