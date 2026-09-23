from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.enrollment import Enrollment
from app.services.enrollments import get_enrollment
from app.services.insights_engine import generate_insights

router = APIRouter(prefix="/insights", tags=["Insights"])


@router.get("/me")
def my_insights(
    remaining_credits: Optional[int] = Query(
        None, ge=1, le=300,
        description="Credits still to take. Estimated from the programme when omitted.",
    ),
    db: Session = Depends(get_db),
    enrollment: Enrollment = Depends(get_enrollment),
):
    """
    Everything the dashboard needs for one programme (current by default):
    standing, trend, courses pulling the CGPA down, strongest courses,
    subject areas, grade spread and suggested next steps.
    """
    return generate_insights(db, enrollment, remaining_credits)
