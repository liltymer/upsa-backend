from typing import Optional

from fastapi import Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.enrollment import Enrollment
from app.models.result import Result
from app.models.student import Student
from app.services.auth import get_current_user
from app.utils.gpa import totals
from app.utils.grading import (
    CLASSIFICATION_BANDS,
    MAX_LEVEL,
    get_academic_standing,
    get_classification,
    parse_academic_year,
    truncate_gpa,
)


def get_enrollment(
    enrollment_id: Optional[int] = Query(
        None, description="Programme to use. Defaults to the student's current programme."
    ),
    db: Session = Depends(get_db),
    current_user: Student = Depends(get_current_user),
) -> Enrollment:
    """
    Resolves the programme a request is about. Students can only reach their own
    enrollments; asking for someone else's returns 404 so ids cannot be probed.
    """
    query = db.query(Enrollment).filter(Enrollment.student_id == current_user.id)

    if enrollment_id is None:
        enrollment = query.filter(Enrollment.is_current.is_(True)).first()
        if enrollment is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No programme on your account yet. Add your programme first.",
            )
        return enrollment

    enrollment = query.filter(Enrollment.id == enrollment_id).first()
    if enrollment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Programme not found.")
    return enrollment


def validate_level(award_type: str, level: int, entry_level: int) -> None:
    if level not in (100, 200, 300, 400):
        raise HTTPException(status_code=400, detail="Level must be 100, 200, 300 or 400.")
    if level < entry_level:
        raise HTTPException(status_code=400, detail=f"Level cannot be below the entry level ({entry_level}).")
    if level > MAX_LEVEL[award_type]:
        raise HTTPException(
            status_code=400,
            detail=f"A {award_type} programme only runs to Level {MAX_LEVEL[award_type]}.",
        )


def start_year_from_current(academic_year: str, current_level: int, entry_level: int) -> str:
    """
    Works out when a programme started from where the student is now.
    Level 200 in 2025/2026 with entry at 100 → started 2024/2025.
    """
    try:
        start = parse_academic_year(academic_year)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    start -= (current_level - entry_level) // 100
    return f"{start}/{start + 1}"


def index_number_taken(db: Session, index_number: str, exclude_enrollment_id: Optional[int] = None) -> bool:
    query = db.query(Enrollment).filter(Enrollment.index_number == index_number)
    if exclude_enrollment_id is not None:
        query = query.filter(Enrollment.id != exclude_enrollment_id)
    return db.query(query.exists()).scalar()


def summarize_enrollment(db: Session, enrollment: Enrollment) -> dict:
    """Programme details plus its own CGPA and classification."""
    results = db.query(Result).filter(Result.enrollment_id == enrollment.id).all()
    points, credits = totals(results)
    cgpa = truncate_gpa(points, credits)
    semesters = {(r.academic_year, r.semester) for r in results}

    return {
        "id": enrollment.id,
        "index_number": enrollment.index_number,
        "programme": enrollment.programme,
        "award_type": enrollment.award_type,
        "entry_level": enrollment.entry_level,
        "current_level": enrollment.current_level,
        "start_academic_year": enrollment.start_academic_year,
        "status": enrollment.status,
        "is_current": enrollment.is_current,
        "is_top_up": enrollment.award_type == "degree" and enrollment.entry_level > 100,
        "needs_review": enrollment.needs_review,
        "cgpa": cgpa,
        "classification": get_classification(cgpa, enrollment.award_type) if results else None,
        "academic_standing": get_academic_standing(cgpa) if results else None,
        "total_credits": credits,
        "total_results": len(results),
        "total_semesters": len(semesters),
        "classification_bands": CLASSIFICATION_BANDS[enrollment.award_type],
    }
