from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.enrollment import Enrollment
from app.models.student import Student
from app.services.auth import get_current_user
from app.services.enrollments import get_enrollment
from app.services.pdf_transcript import create_transcript_pdf
from app.services.transcript_engine import generate_transcript

router = APIRouter(prefix="/transcript", tags=["Transcript"])


def _history(db: Session, student: Student) -> list[dict]:
    """Every programme with results, oldest first (a top-up student's diploma, then degree)."""
    enrollments = (
        db.query(Enrollment)
        .filter(Enrollment.student_id == student.id)
        .order_by(Enrollment.start_academic_year, Enrollment.entry_level, Enrollment.id)
        .all()
    )
    return [t for t in (generate_transcript(db, e) for e in enrollments) if t["transcript"]]


def _safe(label: str) -> str:
    return "".join(c for c in label if c.isalnum() or c in "-_")


@router.get("/me")
def get_my_transcript(
    db: Session = Depends(get_db),
    enrollment: Enrollment = Depends(get_enrollment),
):
    """Transcript for one programme (current by default) as structured JSON."""
    return generate_transcript(db, enrollment)


@router.get("/history")
def get_my_history(
    db: Session = Depends(get_db),
    current_user: Student = Depends(get_current_user),
):
    """Every programme's transcript, oldest first. Each keeps its own CGPA and class."""
    return {"programmes": _history(db, current_user)}


@router.get("/download")
def download_transcript_pdf(
    scope: Literal["programme", "all"] = Query("programme", description='"all" gives the full academic history'),
    db: Session = Depends(get_db),
    current_user: Student = Depends(get_current_user),
    enrollment: Enrollment = Depends(get_enrollment),
):
    """Unofficial transcript PDF for one programme, or the student's full history."""
    if scope == "all":
        content = _history(db, current_user)
        label = f"full_history_{_safe(enrollment.index_number or 'student')}"
    else:
        content = generate_transcript(db, enrollment)
        label = _safe(enrollment.index_number or f"programme-{enrollment.id}")

    if not (content if scope == "all" else content["transcript"]):
        raise HTTPException(status_code=400, detail="No results available to generate a transcript.")

    return StreamingResponse(
        create_transcript_pdf(content),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="transcript_{label}.pdf"'},
    )
