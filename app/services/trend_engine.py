from sqlalchemy.orm import Session
from app.utils.gpa import get_gpa_history


def analyze_gpa_trend(db: Session, student_id: int):

    history = get_gpa_history(db, student_id)

    if len(history) < 2:
        return {
            "trend": "Insufficient Data",
            "message": "At least two semesters required for trend analysis",
            "history": history
        }

    latest = history[-1]["gpa"]
    previous = history[-2]["gpa"]

    trend = "Stable"
    message = "Performance stable"

    if latest > previous:
        trend = "Improving"
        message = "GPA increased compared to previous semester"

    elif latest < previous:
        trend = "Declining"
        message = "GPA decreased compared to previous semester"

    return {
        "trend": trend,
        "message": message,
        "latest_gpa": latest,
        "previous_gpa": previous,
        "history": history
    }