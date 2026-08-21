"""
One-time password reset script for GradeIQ UPSA backend.

Usage:
    python reset_password.py student@example.com

- Prompts you to type a new password (hidden input, typed twice to confirm).
- Hashes it using the exact same bcrypt CryptContext your app already uses.
- Updates the matching Student row and commits.

Run this from your project root (the folder containing `app/`), with your
virtualenv activated, so imports like `app.database` resolve correctly.
"""

import sys
import getpass

from app.database import SessionLocal
from app.models.student import Student
from app.services.auth import hash_password


def reset_password(email: str) -> None:
    db = SessionLocal()
    try:
        student = db.query(Student).filter(Student.email == email).first()

        if student is None:
            print(f"No student found with email: {email}")
            return

        print(f"Found student: {student.name} ({student.index_number})")

        new_password = getpass.getpass("Enter new password: ")
        confirm_password = getpass.getpass("Confirm new password: ")

        if new_password != confirm_password:
            print("Passwords do not match. Aborting.")
            return

        if len(new_password) < 8:
            print("Password should be at least 8 characters. Aborting.")
            return

        student.password_hash = hash_password(new_password)
        db.commit()

        print(f"Password successfully reset for {student.email}.")

    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python reset_password.py <student_email>")
        sys.exit(1)

    reset_password(sys.argv[1])
