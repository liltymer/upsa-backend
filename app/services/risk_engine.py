from sqlalchemy.orm import Session

from app.models.enrollment import Enrollment
from app.utils.gpa import calculate_cgpa
from app.utils.grading import (
    CLASSIFICATION_BANDS,
    PROBATION_THRESHOLD,
    get_classification,
    get_next_band,
)


def analyze_academic_risk(db: Session, enrollment: Enrollment) -> dict:
    """
    Evaluates academic risk for one programme using the official UPSA bands
    for its award type (degree: First Class …, diploma: Distinction …).
    """
    award_type = enrollment.award_type
    cgpa = calculate_cgpa(db, enrollment.id)
    classification = get_classification(cgpa, award_type)
    next_band = get_next_band(cgpa, award_type)
    alerts = []

    if cgpa < PROBATION_THRESHOLD:
        risk_level = "High"
        alerts.append("CGPA below 1.0 — Academic Probation")
    elif classification == "Pass":
        risk_level = "High"
        alerts.append("CGPA in the Pass band — at risk of graduating without a class")
    elif cgpa < 3.0:
        risk_level = "Medium"
        alerts.append(f"CGPA in the {classification} band — improvement needed")
    else:
        risk_level = "Low"
        if next_band:
            alerts.append(f"CGPA in the {classification} band — pushing for {next_band['label']}")

    return {
        "enrollment_id": enrollment.id,
        "programme": enrollment.programme,
        "award_type": award_type,
        "cgpa": cgpa,
        "classification": classification,
        "risk_level": risk_level,
        "alerts": alerts,
        "gap_to_next_class": round(next_band["min"] - cgpa, 2) if next_band else None,
        "next_class": next_band["label"] if next_band else None,
        "classification_bands": CLASSIFICATION_BANDS[award_type],
    }
