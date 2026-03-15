from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.announcement import Announcement
from app.schemas.announcement import AnnouncementResponse

router = APIRouter(prefix="/announcements", tags=["announcements"])


@router.get("/active", response_model=List[AnnouncementResponse])
def get_active_announcements(db: Session = Depends(get_db)):
    """
    Returns all active announcements for students to see on their dashboard.
    No authentication required — public endpoint.
    """
    return (
        db.query(Announcement)
        .filter(Announcement.is_active == True)
        .order_by(Announcement.created_at.desc())
        .limit(5)
        .all()
    )