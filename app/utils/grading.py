# Official UPSA grading scale
# Direction: grade → grade_point
# Students enter their grade (A, B+, etc.) and the system derives the grade point

GRADE_POINTS = {
    "A":  4.0,
    "B+": 3.5,
    "B":  3.0,
    "B-": 2.5,
    "C+": 2.0,
    "C":  1.5,
    "C-": 1.0,
    "D":  0.5,
    "F":  0.0,
}

VALID_GRADES = list(GRADE_POINTS.keys())


def grade_to_point(grade: str) -> float:
    """
    Converts a UPSA grade to its grade point value.
    Raises ValueError if grade is not recognized.
    """
    grade = grade.strip().upper()

    if grade not in GRADE_POINTS:
        raise ValueError(
            f"Invalid grade '{grade}'. "
            f"Valid grades are: {', '.join(VALID_GRADES)}"
        )

    return GRADE_POINTS[grade]


def get_classification(cgpa: float) -> str:
    """
    Returns the degree classification for a given CGPA.
    Based on official UPSA classification bands.
    """
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


def get_academic_standing(cgpa: float) -> str:
    """
    Returns academic standing based on CGPA.
    Probation threshold is below 1.0 per UPSA policy.
    """
    if cgpa < 1.0:
        return "Probation"
    return "Good Standing"