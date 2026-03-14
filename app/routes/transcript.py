from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.auth import get_current_user
from app.models.student import Student
from app.services.transcript_engine import generate_transcript
from app.services.pdf_transcript import create_transcript_pdf

router = APIRouter(prefix="/transcript", tags=["Transcript"])


@router.get("/me")
def get_my_transcript(
    db: Session = Depends(get_db),
    current_user: Student = Depends(get_current_user)
):
    """
    Returns the authenticated student's full academic transcript
    as structured JSON — semester by semester with CGPA.
    """

    transcript = generate_transcript(db, current_user.id)

    if not transcript:
        raise HTTPException(
            status_code=404,
            detail="No transcript found. Add your semester results first."
        )

    return transcript


@router.get("/download")
def download_transcript_pdf(
    db: Session = Depends(get_db),
    current_user: Student = Depends(get_current_user)
):
    """
    Generates and serves the student's academic transcript as a
    downloadable PDF file using the official UPSA brand colors.
    """

    transcript = generate_transcript(db, current_user.id)

    if not transcript:
        raise HTTPException(
            status_code=404,
            detail="No transcript found. Add your semester results first."
        )

    if not transcript.get("transcript"):
        raise HTTPException(
            status_code=400,
            detail="No results available to generate a transcript."
        )

    pdf_buffer = create_transcript_pdf(transcript)

    filename = f"transcript_{current_user.index_number}.pdf"

    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )