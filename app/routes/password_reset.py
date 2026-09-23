import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, Field

from app.database import get_db
from app.models.student import Student
from app.models.password_reset import PasswordResetToken
from app.services.email import send_reset_email
from app.services.auth import hash_password, verify_password
from app.services.password_policy import PASSWORD_MAX_LENGTH, password_error
from app.services.rate_limit import rate_limit

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Password Reset"])


# ================================
# SCHEMAS
# ================================

class ForgotPasswordRequest(BaseModel):
    email: EmailStr


def is_expired(expires_at: datetime) -> bool:
    # Postgres returns timezone-aware values; SQLite (local/tests) returns naive UTC
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return expires_at < datetime.now(timezone.utc)


def hash_token(token: str) -> str:
    """Reset tokens are stored as SHA-256 so a database leak cannot be used to reset passwords."""
    return hashlib.sha256(token.encode()).hexdigest()


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=1, max_length=PASSWORD_MAX_LENGTH)


# ================================
# FORGOT PASSWORD
# ================================

@router.post(
    "/forgot-password",
    dependencies=[Depends(rate_limit("forgot-password", limit=5, window_seconds=900))],
)
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
        func.lower(Student.email) == data.email.strip().lower()
    ).first()

    # Always return success — never reveal if email exists
    if not student:
        return {
            "message": "If that email is registered, a reset link has been sent."
        }

    # Invalidate any existing unused tokens for this student
    db.query(PasswordResetToken).filter(
        PasswordResetToken.student_id == student.id,
        PasswordResetToken.is_used.is_(False),
    ).delete()
    db.commit()

    # Generate secure token
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

    reset_token = PasswordResetToken(
        student_id=student.id,
        token=hash_token(token),
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
    except Exception:
        # Don't expose email errors to user
        logger.exception("Failed to send password reset email to student %s", student.id)

    return {
        "message": "If that email is registered, a reset link has been sent."
    }


# ================================
# VERIFY TOKEN
# ================================

@router.get(
    "/verify-reset-token/{token}",
    dependencies=[Depends(rate_limit("verify-reset", limit=30, window_seconds=900))],
)
def verify_reset_token(token: str, db: Session = Depends(get_db)):
    """
    Checks if a reset token is valid and not expired.
    Called by the frontend before showing the new password form.
    """
    reset_token = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == hash_token(token),
        PasswordResetToken.is_used.is_(False),
    ).first()

    if not reset_token:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired reset link."
        )

    if is_expired(reset_token.expires_at):
        raise HTTPException(
            status_code=400,
            detail="This reset link has expired. Please request a new one."
        )

    return {"valid": True, "message": "Token is valid."}


# ================================
# RESET PASSWORD
# ================================

@router.post(
    "/reset-password",
    dependencies=[Depends(rate_limit("reset-password", limit=10, window_seconds=900))],
)
def reset_password(
    data: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    """
    Accepts a token and new password.
    Updates the student's password and marks the token as used.
    """
    reset_token = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == hash_token(data.token),
        PasswordResetToken.is_used.is_(False),
    ).first()

    if not reset_token:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired reset link."
        )

    if is_expired(reset_token.expires_at):
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

    weakness = password_error(data.new_password, email=student.email, name=student.name)
    if weakness:
        raise HTTPException(status_code=400, detail=weakness)
    if verify_password(data.new_password, student.password_hash):
        raise HTTPException(status_code=400, detail="Choose a password you have not used on this account before.")

    student.password_hash = hash_password(data.new_password)
    reset_token.is_used = True

    db.commit()

    return {"message": "Password reset successfully. You can now log in."}