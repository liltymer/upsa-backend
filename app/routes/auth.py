from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from typing import Literal

from app.database import get_db
from app.models.student import Student
from app.services.auth import (
    hash_password,
    verify_password,
    create_access_token
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ================================
# REQUEST SCHEMAS
# ================================

class RegisterRequest(BaseModel):
    name: str
    index_number: str
    email: EmailStr
    password: str
    programme: str
    level: Literal[100, 200, 300, 400]
    academic_year: str  # e.g. "2024/2025"


# ================================
# REGISTER
# ================================

@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    """
    Register a new student account.
    Requires personal info + academic details.
    """

    # Check for existing student
    existing = db.query(Student).filter(
        (Student.email == data.email) |
        (Student.index_number == data.index_number)
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A student with this email or index number already exists."
        )

    # Validate academic year format
    if "/" not in data.academic_year:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Academic year must be in format YYYY/YYYY e.g. 2024/2025"
        )

    new_student = Student(
        name=data.name,
        index_number=data.index_number,
        email=data.email,
        password_hash=hash_password(data.password),
        programme=data.programme,
        level=data.level,
        academic_year=data.academic_year,
    )

    db.add(new_student)
    db.commit()
    db.refresh(new_student)

    return {
        "message": "Account created successfully. You can now sign in.",
        "name": new_student.name,
        "index_number": new_student.index_number,
        "programme": new_student.programme,
        "level": new_student.level,
        "academic_year": new_student.academic_year,
    }


# ================================
# LOGIN
# ================================

@router.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Login with email and password.
    Returns a JWT access token.
    """

    user = db.query(Student).filter(
        Student.email == form_data.username
    ).first()

    if not user or not verify_password(
        form_data.password,
        user.password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token({"sub": str(user.id)})

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }