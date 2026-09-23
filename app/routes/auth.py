from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import Literal, Optional

from app.config import PASSWORD_MIN_LENGTH
from app.database import get_db
from app.models.enrollment import Enrollment
from app.models.student import Student
from app.schemas.enrollment import PreviousProgramme
from app.services.auth import (
    hash_password,
    verify_password,
    create_access_token
)
from app.services.enrollments import (
    index_number_taken,
    start_year_from_current,
    validate_level,
)
from app.services.rate_limit import rate_limit
from app.utils.grading import award_type_for_programme, parse_academic_year

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ================================
# REQUEST SCHEMAS
# ================================

class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    index_number: str = Field(min_length=1, max_length=30)
    email: EmailStr
    password: str = Field(min_length=PASSWORD_MIN_LENGTH, max_length=128)
    programme: str = Field(min_length=1, max_length=200)
    level: Literal[100, 200, 300, 400]
    academic_year: str  # current academic year, e.g. "2025/2026"
    # Top-up students entered their degree at Level 300 after a diploma
    is_top_up: bool = False
    previous_programme: Optional[PreviousProgramme] = None


def normalize_index(value: str) -> str:
    return value.strip().upper()


# ================================
# REGISTER
# ================================

@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit("register", limit=10, window_seconds=3600))],
)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    """
    Register a new student account with their current programme.
    Top-up students can also record the diploma they completed.
    """
    email = data.email.strip().lower()
    index_number = normalize_index(data.index_number)
    programme = data.programme.strip()
    award_type = award_type_for_programme(programme)
    entry_level = 300 if data.is_top_up else 100

    try:
        parse_academic_year(data.academic_year)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    if data.is_top_up and award_type != "degree":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A top-up must be a degree programme.",
        )
    validate_level(award_type, data.level, entry_level)

    previous_index = None
    if data.previous_programme and data.previous_programme.index_number:
        previous_index = normalize_index(data.previous_programme.index_number)
        if previous_index == index_number:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Your previous programme should have a different index number.",
            )

    email_taken = db.query(Student).filter(func.lower(Student.email) == email).first()
    if email_taken or index_number_taken(db, index_number) or (
        previous_index and index_number_taken(db, previous_index)
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A student with this email or index number already exists. "
                   "If this is your old account, sign in and link it instead.",
        )

    student = Student(
        name=data.name.strip(),
        email=email,
        password_hash=hash_password(data.password),
        role="student",
    )
    db.add(student)
    db.flush()

    current = Enrollment(
        student_id=student.id,
        index_number=index_number,
        programme=programme,
        award_type=award_type,
        entry_level=entry_level,
        current_level=data.level,
        start_academic_year=start_year_from_current(data.academic_year, data.level, entry_level),
        status="active",
        is_current=True,
    )
    db.add(current)

    if data.previous_programme:
        prev = data.previous_programme
        try:
            parse_academic_year(prev.start_academic_year)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
        prev_award = award_type_for_programme(prev.programme)
        db.add(Enrollment(
            student_id=student.id,
            index_number=previous_index,
            programme=prev.programme.strip(),
            award_type=prev_award,
            entry_level=100,
            current_level=200 if prev_award == "diploma" else 400,
            start_academic_year=prev.start_academic_year.strip(),
            status="completed",
            is_current=False,
        ))

    db.commit()

    return {
        "message": "Account created successfully. You can now sign in.",
        "name": student.name,
        "index_number": current.index_number,
        "programme": current.programme,
        "level": current.current_level,
        "academic_year": data.academic_year.strip(),
    }


# ================================
# LOGIN
# ================================

@router.post(
    "/login",
    dependencies=[Depends(rate_limit("login", limit=10, window_seconds=300))],
)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Login with email or any index number the student has held
    (a top-up student can use their diploma or degree index number).
    Returns a JWT access token.
    """
    username = form_data.username.strip()

    if "@" in username:
        user = db.query(Student).filter(func.lower(Student.email) == username.lower()).first()
    else:
        enrollment = db.query(Enrollment).filter(
            Enrollment.index_number == normalize_index(username)
        ).first()
        user = enrollment.student if enrollment else None

    if not verify_password(form_data.password, user.password_hash if user else None):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email/index number or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token({"sub": str(user.id)})

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }
