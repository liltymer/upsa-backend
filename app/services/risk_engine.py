from sqlalchemy.orm import Session
from app.utils.gpa import calculate_cgpa


def analyze_academic_risk(db: Session, student_id: int) -> dict:
    """
    Evaluates academic risk based on official UPSA CGPA bands.
    Returns risk level, alerts, and exact gap to next classification.
    """
    cgpa = calculate_cgpa(db, student_id)

    alerts = []
    risk_level = "Low"

    # Risk level assessment
    if cgpa < 1.0:
        alerts.append("CGPA below 1.0 — Academic Probation")
        risk_level = "High"
    elif cgpa < 2.0:
        alerts.append("CGPA in Pass zone — at risk of not graduating with a class")
        risk_level = "High"
    elif cgpa < 2.5:
        alerts.append("CGPA in Third Class zone — improvement needed")
        risk_level = "Medium"
    elif cgpa < 3.0:
        alerts.append("CGPA in Second Class Lower zone")
        risk_level = "Medium"
    elif cgpa < 3.6:
        alerts.append("CGPA in Second Class Upper zone — pushing for First Class")
        risk_level = "Low"

    # Gap to next classification
    gap_to_next = None
    next_class = None

    if cgpa < 1.0:
        gap_to_next = round(1.0 - cgpa, 2)
        next_class = "Pass"
    elif cgpa < 2.0:
        gap_to_next = round(2.0 - cgpa, 2)
        next_class = "Third Class"
    elif cgpa < 2.5:
        gap_to_next = round(2.5 - cgpa, 2)
        next_class = "Second Class Lower"
    elif cgpa < 3.0:
        gap_to_next = round(3.0 - cgpa, 2)
        next_class = "Second Class Upper"
    elif cgpa < 3.6:
        gap_to_next = round(3.6 - cgpa, 2)
        next_class = "First Class"

    return {
        "cgpa": cgpa,
        "classification": _classify(cgpa),
        "risk_level": risk_level,
        "alerts": alerts,
        "gap_to_next_class": gap_to_next,
        "next_class": next_class
    }


def _classify(cgpa: float) -> str:
    if cgpa >= 3.6:
        return "First Class"
    elif cgpa >= 3.0:
        return "Second Class Upper"
    elif cgpa >= 2.5:
        return "Second Class Lower"
    elif cgpa >= 2.0:
        return "Third Class"
    elif cgpa >= 1.0:
        return "Pass"
    else:
        return "Fail"