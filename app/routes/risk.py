from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.enrollment import Enrollment
from app.services.enrollments import get_enrollment
from app.services.risk_engine import analyze_academic_risk

router = APIRouter(prefix="/risk", tags=["Academic Risk"])


@router.get("/me")
def get_risk_analysis(
    db: Session = Depends(get_db),
    enrollment: Enrollment = Depends(get_enrollment),
):
    return {
        "enrollment_id": enrollment.id,
        "risk_analysis": analyze_academic_risk(db, enrollment),
    }
