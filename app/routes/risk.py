from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.auth import get_current_user
from app.models.student import Student
from app.services.risk_engine import analyze_academic_risk

router = APIRouter(prefix="/risk", tags=["Academic Risk"])


@router.get("/me")
def get_risk_analysis(
    db: Session = Depends(get_db),
    current_user: Student = Depends(get_current_user)
):

    analysis = analyze_academic_risk(db, current_user.id)

    return {
        "student_id": current_user.id,
        "risk_analysis": analysis
    }