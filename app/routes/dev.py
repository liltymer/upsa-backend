from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.result import Result
from app.models.student import Student
from app.utils.grading import grade_to_point

router = APIRouter(prefix="/dev", tags=["Dev"])


@router.post("/seed")
def seed(db: Session = Depends(get_db)):
    """
    Clears all results and seeds fresh sample data
    for the first registered student.
    For development use only — remove in production.
    """

    # Clear existing results only — keep students
    db.query(Result).delete()
    db.commit()

    # Get first student
    student = db.query(Student).first()

    if not student:
        return {
            "status": "No students found.",
            "message": "Register a student first, then run seed again."
        }

    # Sample results — UPSA style, grade only, no scores
    sample_results = [

        # Year 1 — Semester 1
        {
            "course_code": "DIPC003",
            "course_name": "Business Management",
            "credit_hours": 3,
            "grade": "B-",
            "year": 1, "semester": 1
        },
        {
            "course_code": "DIPC005",
            "course_name": "Business Mathematics",
            "credit_hours": 3,
            "grade": "C-",
            "year": 1, "semester": 1
        },
        {
            "course_code": "DIPC009",
            "course_name": "Introduction to Information Technology",
            "credit_hours": 3,
            "grade": "B+",
            "year": 1, "semester": 1
        },
        {
            "course_code": "DIPT001",
            "course_name": "Computer Applications in Business",
            "credit_hours": 3,
            "grade": "A",
            "year": 1, "semester": 1
        },
        {
            "course_code": "DIPT003",
            "course_name": "Programming I",
            "credit_hours": 3,
            "grade": "A",
            "year": 1, "semester": 1
        },

        # Year 1 — Semester 2
        {
            "course_code": "DIPC006",
            "course_name": "Principles of Accounting",
            "credit_hours": 3,
            "grade": "B",
            "year": 1, "semester": 2
        },
        {
            "course_code": "DIPC010",
            "course_name": "Communication Skills",
            "credit_hours": 2,
            "grade": "A",
            "year": 1, "semester": 2
        },
        {
            "course_code": "DIPT004",
            "course_name": "Database Management Systems",
            "credit_hours": 3,
            "grade": "B+",
            "year": 1, "semester": 2
        },
        {
            "course_code": "DIPT006",
            "course_name": "Programming II",
            "credit_hours": 3,
            "grade": "B",
            "year": 1, "semester": 2
        },

    ]

    created = 0
    for entry in sample_results:
        grade_point = grade_to_point(entry["grade"])

        result = Result(
            student_id=student.id,
            course_code=entry["course_code"],
            course_name=entry["course_name"],
            credit_hours=entry["credit_hours"],
            grade=entry["grade"],
            grade_point=grade_point,
            year=entry["year"],
            semester=entry["semester"],
        )
        db.add(result)
        created += 1

    db.commit()

    return {
        "status": "Seeded successfully.",
        "student": student.name,
        "programme": student.programme,
        "level": student.level,
        "semesters_seeded": 2,
        "results_created": created,
        "note": "All grades are UPSA-style — no scores."
    }


@router.delete("/reset")
def reset(db: Session = Depends(get_db)):
    """
    Clears ALL results for all students.
    Use this to start fresh during development.
    """
    db.query(Result).delete()
    db.commit()

    return {
        "status": "All results cleared.",
        "message": "Student accounts preserved. Results wiped."
    }