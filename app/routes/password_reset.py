import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models.student import Student
from app.models.password_reset import PasswordResetToken
from app.services.email import send_reset_email
from app.services.auth import hash_password

router = APIRouter(prefix="/auth", tags=["Password Reset"])


# ================================
# SCHEMAS
# ================================

class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


# ================================
# FORGOT PASSWORD
# ================================

@router.post("/forgot-password")
def forgot_password(
    data: ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    """
    Accepts an email address.
    If a student with that email exists, sends a reset link.
    Always returns success to prevent email enumeration.
    """
    student = db.query(Student).filter(
        Student.email == data.email
    ).first()

    # Always return success — never reveal if email exists
    if not student:
        return {
            "message": "If that email is registered, a reset link has been sent."
        }

    # Invalidate any existing unused tokens for this student
    db.query(PasswordResetToken).filter(
        PasswordResetToken.student_id == student.id,
        PasswordResetToken.is_used == False,
    ).delete()
    db.commit()

    # Generate secure token
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

    reset_token = PasswordResetToken(
        student_id=student.id,
        token=token,
        expires_at=expires_at,
    )
    db.add(reset_token)
    db.commit()

    # Send email
    try:
        send_reset_email(
            to_email=student.email,
            student_name=student.name,
            reset_token=token,
        )
    except Exception as e:
        # Don't expose email errors to user
        print(f"Email error: {e}")

    return {
        "message": "If that email is registered, a reset link has been sent."
    }


# ================================
# VERIFY TOKEN
# ================================

@router.get("/verify-reset-token/{token}")
def verify_reset_token(token: str, db: Session = Depends(get_db)):
    """
    Checks if a reset token is valid and not expired.
    Called by the frontend before showing the new password form.
    """
    reset_token = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == token,
        PasswordResetToken.is_used == False,
    ).first()

    if not reset_token:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired reset link."
        )

    if reset_token.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=400,
            detail="This reset link has expired. Please request a new one."
        )

    return {"valid": True, "message": "Token is valid."}


# ================================
# RESET PASSWORD
# ================================

@router.post("/reset-password")
def reset_password(
    data: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    """
    Accepts a token and new password.
    Updates the student's password and marks the token as used.
    """
    if len(data.new_password) < 6:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 6 characters."
        )

    reset_token = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == data.token,
        PasswordResetToken.is_used == False,
    ).first()

    if not reset_token:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired reset link."
        )

    if reset_token.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=400,
            detail="This reset link has expired. Please request a new one."
        )

    # Update password
    student = db.query(Student).filter(
        Student.id == reset_token.student_id
    ).first()

    if not student:
        raise HTTPException(status_code=404, detail="Student not found.")

    student.password_hash = hash_password(data.new_password)
    reset_token.is_used = True

    db.commit()

    return {"message": "Password reset successfully. You can now log in."}