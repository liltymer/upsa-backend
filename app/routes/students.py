from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.password_reset import PasswordResetToken
from app.models.student import Student
from app.services.auth import get_current_user, hash_password, verify_password
from app.services.password_policy import PASSWORD_MAX_LENGTH, password_error
from app.services.rate_limit import rate_limit
from app.services.enrollments import summarize_enrollment
from app.utils.grading import current_academic_year

router = APIRouter(prefix="/students", tags=["Students"])


class ProfileUpdate(BaseModel):
    """Account details only: programme details are edited per programme via /enrollments."""
    name: Optional[str] = Field(None, min_length=2, max_length=120)
    # Empty string clears it
    preferred_name: Optional[str] = Field(None, max_length=60)


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=PASSWORD_MAX_LENGTH)
    new_password: str = Field(min_length=1, max_length=PASSWORD_MAX_LENGTH)


class AccountDeletion(BaseModel):
    password: str = Field(min_length=1, max_length=PASSWORD_MAX_LENGTH)
    confirm: Literal["DELETE"]


def _profile(db: Session, student: Student) -> dict:
    current = student.current_enrollment
    return {
        "id": student.id,
        "name": student.name,
        "preferred_name": student.preferred_name,
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
    if data.name is not None:
        name = data.name.strip()
        if len(name) < 2:
            raise HTTPException(status_code=400, detail="Name must be at least 2 characters.")
        current_user.name = name
    if data.preferred_name is not None:
        current_user.preferred_name = data.preferred_name.strip() or None
    db.commit()
    db.refresh(current_user)

    return {"message": "Profile updated successfully.", **_profile(db, current_user)}


# ================================
# CHANGE PASSWORD
# ================================

@router.post(
    "/me/password",
    dependencies=[Depends(rate_limit("change-password", limit=10, window_seconds=900))],
)
def change_my_password(
    data: PasswordChange,
    db: Session = Depends(get_db),
    current_user: Student = Depends(get_current_user),
):
    """Change the password while signed in. The current password is required."""
    if not verify_password(data.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Your current password is not correct.")
    weakness = password_error(data.new_password, email=current_user.email, name=current_user.name)
    if weakness:
        raise HTTPException(status_code=400, detail=weakness)
    if verify_password(data.new_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Choose a password different from your current one.")
    current_user.password_hash = hash_password(data.new_password)
    db.commit()
    return {"message": "Password changed."}


# ================================
# DELETE MY ACCOUNT
# ================================

@router.delete(
    "/me",
    dependencies=[Depends(rate_limit("delete-account", limit=5, window_seconds=900))],
)
def delete_my_account(
    data: AccountDeletion,
    db: Session = Depends(get_db),
    current_user: Student = Depends(get_current_user),
):
    """
    Permanently removes the account with every programme and result.
    Needs the password and the word DELETE. Admin accounts are removed by another admin.
    """
    if current_user.role == "admin":
        raise HTTPException(status_code=400, detail="Admin accounts cannot be deleted from the profile page.")
    if not verify_password(data.password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Your password is not correct.")
    db.query(PasswordResetToken).filter(PasswordResetToken.student_id == current_user.id).delete()
    db.delete(current_user)
    db.commit()
    return {"message": "Your account and all your results have been deleted."}
