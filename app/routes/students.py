from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.student import Student
from app.services.auth import get_current_user
from app.services.enrollments import summarize_enrollment
from app.utils.grading import current_academic_year

router = APIRouter(prefix="/students", tags=["Students"])


class ProfileUpdate(BaseModel):
    """Account details only — programme details are edited per programme via /enrollments."""
    name: str = Field(min_length=2, max_length=120)


def _profile(db: Session, student: Student) -> dict:
    current = student.current_enrollment
    return {
        "id": student.id,
        "name": student.name,
        "email": student.email,
        "role": student.role,
        # Current programme, kept at top level for existing screens
        "index_number": current.index_number if current else None,
        "programme": current.programme if current else None,
        "level": current.current_level if current else None,
        "academic_year": current_academic_year(),
        "enrollments": [summarize_enrollment(db, e) for e in student.enrollments],
    }


# ================================
# GET MY PROFILE
# ================================

@router.get("/me")
def get_my_profile(
    db: Session = Depends(get_db),
    current_user: Student = Depends(get_current_user),
):
    return _profile(db, current_user)


# ================================
# UPDATE MY PROFILE
# ================================

@router.put("/me")
def update_my_profile(
    data: ProfileUpdate,
    db: Session = Depends(get_db),
    current_user: Student = Depends(get_current_user),
):
    name = data.name.strip()
    if len(name) < 2:
        raise HTTPException(status_code=400, detail="Name must be at least 2 characters.")

    current_user.name = name
    db.commit()
    db.refresh(current_user)

    return {"message": "Profile updated successfully.", **_profile(db, current_user)}
