from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.models.student import Student
from app.services.auth import get_current_user

router = APIRouter(prefix="/students", tags=["Students"])


# ================================
# SCHEMA
# ================================

class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    programme: Optional[str] = None
    level: Optional[int] = None
    academic_year: Optional[str] = None


# ================================
# EXISTING — Create student
# ================================

@router.post("/")
def create_student(
    name: str,
    index_number: str,
    db: Session = Depends(get_db)
):
    existing = db.query(Student).filter(
        Student.index_number == index_number
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Student already exists"
        )

    student = Student(name=name, index_number=index_number)
    db.add(student)
    db.commit()
    db.refresh(student)
    return student


# ================================
# GET MY PROFILE
# ================================

@router.get("/me")
def get_my_profile(
    db: Session = Depends(get_db),
    current_user: Student = Depends(get_current_user),
):
    return {
        "id": current_user.id,
        "name": current_user.name,
        "index_number": current_user.index_number,
        "email": current_user.email,
        "programme": current_user.programme,
        "level": current_user.level,
        "academic_year": current_user.academic_year,
        "role": current_user.role,
    }


# ================================
# UPDATE MY PROFILE
# ================================

@router.put("/me")
def update_my_profile(
    data: ProfileUpdate,
    db: Session = Depends(get_db),
    current_user: Student = Depends(get_current_user),
):
    if data.name is not None:
        if len(data.name.strip()) < 2:
            raise HTTPException(
                status_code=400,
                detail="Name must be at least 2 characters."
            )
        current_user.name = data.name.strip()

    if data.programme is not None:
        current_user.programme = data.programme

    if data.level is not None:
        if data.level not in [100, 200, 300, 400]:
            raise HTTPException(
                status_code=400,
                detail="Level must be 100, 200, 300 or 400."
            )
        current_user.level = data.level

    if data.academic_year is not None:
        current_user.academic_year = data.academic_year

    db.commit()
    db.refresh(current_user)

    return {
        "message": "Profile updated successfully.",
        "name": current_user.name,
        "programme": current_user.programme,
        "level": current_user.level,
        "academic_year": current_user.academic_year,
    }