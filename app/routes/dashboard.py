from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.enrollment import Enrollment
from app.models.student import Student
from app.services.auth import get_current_user
from app.services.enrollments import get_enrollment, summarize_enrollment
from app.utils.grading import current_academic_year

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/me")
def get_my_dashboard(
    db: Session = Depends(get_db),
    current_user: Student = Depends(get_current_user),
    enrollment: Enrollment = Depends(get_enrollment),
):
    """
    Headline figures for one programme (current by default), plus a summary of
    the student's other programmes: e.g. a completed diploma before a top-up.
    """
    summary = summarize_enrollment(db, enrollment)
    others = [
        summarize_enrollment(db, e)
        for e in current_user.enrollments
        if e.id != enrollment.id
    ]

    return {
        "name": current_user.name,
        "role": current_user.role,
        "enrollment_id": enrollment.id,
        "index_number": enrollment.index_number,
        "programme": enrollment.programme,
        "award_type": enrollment.award_type,
        "level": enrollment.current_level,
        "academic_year": current_academic_year(),
        "is_top_up": summary["is_top_up"],
        "status": enrollment.status,
        "cgpa": summary["cgpa"],
        "classification": summary["classification"] or "No results yet",
        "academic_standing": summary["academic_standing"] or "Good Standing",
        "classification_bands": summary["classification_bands"],
        "other_programmes": others,
        "needs_review": summary["needs_review"] or any(o["needs_review"] for o in others),
    }
