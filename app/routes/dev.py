from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.enrollment import Enrollment
from app.models.result import Result
from app.services.auth import require_admin
from app.utils.grading import format_academic_year, grade_to_point, parse_academic_year

# Only mounted when ENVIRONMENT=development (see app/main.py),
# and even then restricted to admins.
router = APIRouter(
    prefix="/dev",
    tags=["Dev"],
    dependencies=[Depends(require_admin)],
)


@router.post("/seed")
def seed(db: Session = Depends(get_db)):
    """
    Clears all results and seeds fresh sample data
    for the first registered student.
    For development use only: remove in production.
    """

    # Clear existing results only: keep students
    db.query(Result).delete()
    db.commit()

    # Current programme of the first registered student
    enrollment = (
        db.query(Enrollment)
        .filter(Enrollment.is_current.is_(True))
        .order_by(Enrollment.id)
        .first()
    )

    if not enrollment:
        return {
            "status": "No students found.",
            "message": "Register a student first, then run seed again."
        }
    student = enrollment.student
    start_year = parse_academic_year(enrollment.start_academic_year)

    # Sample results: UPSA style, grade only, no scores
    sample_results = [

        # Year 1: Semester 1
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

        # Year 1: Semester 2
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
            enrollment_id=enrollment.id,
            course_code=entry["course_code"],
            course_name=entry["course_name"],
            credit_hours=entry["credit_hours"],
            grade=entry["grade"],
            grade_point=grade_point,
            academic_year=format_academic_year(start_year + entry["year"] - 1),
            semester=entry["semester"],
        )
        db.add(result)
        created += 1

    db.commit()

    return {
        "status": "Seeded successfully.",
        "student": student.name,
        "programme": enrollment.programme,
        "level": enrollment.current_level,
        "semesters_seeded": 2,
        "results_created": created,
        "note": "All grades are UPSA-style. No scores."
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