from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.student import Student
from app.services.auth import get_current_user

from app.utils.gpa import (
    calculate_semester_gpa,
    calculate_cgpa,
    get_gpa_history
)

router = APIRouter(prefix="/gpa", tags=["GPA"])


@router.get("/semester")
def semester_gpa(
    year: int,
    semester: int,
    db: Session = Depends(get_db),
    current_user: Student = Depends(get_current_user)
):

    gpa = calculate_semester_gpa(db, current_user.id, year, semester)

    return {
        "student_id": current_user.id,
        "year": year,
        "semester": semester,
        "semester_gpa": gpa
    }


@router.get("/cgpa")
def cgpa(
    db: Session = Depends(get_db),
    current_user: Student = Depends(get_current_user)
):

    cgpa_value = calculate_cgpa(db, current_user.id)

    return {
        "student_id": current_user.id,
        "cgpa": cgpa_value
    }


@router.get("/history")
def gpa_history(
    db: Session = Depends(get_db),
    current_user: Student = Depends(get_current_user)
):

    history = get_gpa_history(db, current_user.id)

    return {
        "student_id": current_user.id,
        "gpa_history": history
    }