from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.enrollment import Enrollment
from app.services.enrollments import get_enrollment
from app.services.pdf_transcript import create_transcript_pdf
from app.services.transcript_engine import generate_transcript

router = APIRouter(prefix="/transcript", tags=["Transcript"])


@router.get("/me")
def get_my_transcript(
    db: Session = Depends(get_db),
    enrollment: Enrollment = Depends(get_enrollment),
):
    """Transcript for one programme (current by default) as structured JSON."""
    return generate_transcript(db, enrollment)


@router.get("/download")
def download_transcript_pdf(
    db: Session = Depends(get_db),
    enrollment: Enrollment = Depends(get_enrollment),
):
    """The programme's unofficial transcript as a downloadable PDF."""
    transcript = generate_transcript(db, enrollment)

    if not transcript["transcript"]:
        raise HTTPException(
            status_code=400,
            detail="No results available to generate a transcript.",
        )

    pdf_buffer = create_transcript_pdf(transcript)
    label = enrollment.index_number or f"programme-{enrollment.id}"
    safe_label = "".join(c for c in label if c.isalnum() or c in "-_")
    filename = f"transcript_{safe_label}.pdf"

    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )
