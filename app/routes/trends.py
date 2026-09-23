from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.enrollment import Enrollment
from app.services.enrollments import get_enrollment
from app.services.trend_engine import analyze_gpa_trend

router = APIRouter(prefix="/trends", tags=["GPA Trends"])


@router.get("/me")
def get_gpa_trend(
    db: Session = Depends(get_db),
    enrollment: Enrollment = Depends(get_enrollment),
):
    return {
        "enrollment_id": enrollment.id,
        "trend_analysis": analyze_gpa_trend(db, enrollment.id),
    }
