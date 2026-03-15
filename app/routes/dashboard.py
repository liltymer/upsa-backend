from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.auth import get_current_user
from app.models.student import Student
from app.utils.gpa import calculate_cgpa

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


def classify_cgpa(cgpa: float) -> str:
    if cgpa >= 3.6:
        return "First Class"
    elif cgpa >= 3.0:
        return "Second Class Upper"
    elif cgpa >= 2.5:
        return "Second Class Lower"
    elif cgpa >= 2.0:
        return "Third Class"
    elif cgpa >= 1.0:
        return "Pass"
    else:
        return "Fail"


def academic_standing(cgpa: float) -> str:
    if cgpa < 1.0:
        return "Probation"
    return "Good Standing"


@router.get("/me")
def get_my_dashboard(
    db: Session = Depends(get_db),
    current_user: Student = Depends(get_current_user)
):
    cgpa = calculate_cgpa(db, current_user.id)
    classification = classify_cgpa(cgpa)
    standing = academic_standing(cgpa)

    return {
        "name": current_user.name,
        "index_number": current_user.index_number,
        "cgpa": round(cgpa, 2),
        "classification": classification,
        "academic_standing": standing,
        "academic_year": current_user.academic_year,
        "programme": current_user.programme,
        "level": current_user.level,
        "role": current_user.role,  # ← ADDED
    }