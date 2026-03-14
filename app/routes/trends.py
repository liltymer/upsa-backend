from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.auth import get_current_user
from app.models.student import Student
from app.services.trend_engine import analyze_gpa_trend

router = APIRouter(prefix="/trends", tags=["GPA Trends"])


@router.get("/me")
def get_gpa_trend(
    db: Session = Depends(get_db),
    current_user: Student = Depends(get_current_user)
):

    trend = analyze_gpa_trend(db, current_user.id)

    return {
        "student_id": current_user.id,
        "trend_analysis": trend
    }