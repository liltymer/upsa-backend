"""
One-time password reset script for GradeIQ UPSA backend.

Usage:
    python -m app.reset_password student@example.com

- Prompts you to type a new password (hidden input, typed twice to confirm).
- Hashes it using the exact same bcrypt CryptContext your app already uses.
- Updates the matching Student row and commits.

Run this from your project root (the folder containing `app/`), with your
virtualenv activated and DATABASE_URL pointing at the database you mean to change.
"""

import sys
import getpass

from sqlalchemy import func

from app.config import PASSWORD_MIN_LENGTH
from app.database import SessionLocal
import app.models  # noqa: F401 — registers every model so relationships resolve
from app.models.student import Student
from app.services.auth import hash_password


def reset_password(email: str) -> None:
    db = SessionLocal()
    try:
        student = db.query(Student).filter(
            func.lower(Student.email) == email.strip().lower()
        ).first()

        if student is None:
            print(f"No student found with email: {email}")
            return

        current = student.current_enrollment
        index_number = current.index_number if current else "no programme"
        print(f"Found student: {student.name} ({index_number})")

        new_password = getpass.getpass("Enter new password: ")
        confirm_password = getpass.getpass("Confirm new password: ")

        if new_password != confirm_password:
            print("Passwords do not match. Aborting.")
            return

        if len(new_password) < PASSWORD_MIN_LENGTH:
            print(f"Password should be at least {PASSWORD_MIN_LENGTH} characters. Aborting.")
            return

        student.password_hash = hash_password(new_password)
        db.commit()

        print(f"Password successfully reset for {student.email}.")

    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python -m app.reset_password <student_email>")
        sys.exit(1)

    reset_password(sys.argv[1])
