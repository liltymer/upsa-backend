# Official UPSA grading scale — identical for diploma and degree programmes.
# Students enter their grade (A, B+, etc.) and the system derives the grade point.
# Classification bands differ: degrees use First Class … Pass, diplomas use Distinction … Pass.

import re
from datetime import date
from decimal import Decimal, ROUND_DOWN
from typing import Literal, Optional

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

GRADE_SCALE = [
    {"grade": "A",  "marks": "80-100", "interpretation": "Excellent",       "grade_point": 4.0},
    {"grade": "B+", "marks": "75-79",  "interpretation": "Very Good",       "grade_point": 3.5},
    {"grade": "B",  "marks": "70-74",  "interpretation": "Good",            "grade_point": 3.0},
    {"grade": "B-", "marks": "65-69",  "interpretation": "Above Average",   "grade_point": 2.5},
    {"grade": "C+", "marks": "60-64",  "interpretation": "Average",         "grade_point": 2.0},
    {"grade": "C",  "marks": "55-59",  "interpretation": "Below Average",   "grade_point": 1.5},
    {"grade": "C-", "marks": "50-54",  "interpretation": "Marginal Pass",   "grade_point": 1.0},
    {"grade": "D",  "marks": "45-49",  "interpretation": "Unsatisfactory",  "grade_point": 0.5},
    {"grade": "F",  "marks": "0-44",   "interpretation": "Fail",            "grade_point": 0.0},
]

AwardType = Literal["diploma", "degree"]

# Highest band first. "min" is inclusive.
# The official diploma chart lists Credit as 2.5–3.49 and Distinction from 3.6,
# so 3.50–3.59 is treated as Credit.
CLASSIFICATION_BANDS: dict[str, list[dict]] = {
    "degree": [
        {"label": "First Class",        "min": 3.6, "range": "3.60 - 4.00"},
        {"label": "Second Class Upper", "min": 3.0, "range": "3.00 - 3.59"},
        {"label": "Second Class Lower", "min": 2.5, "range": "2.50 - 2.99"},
        {"label": "Third Class",        "min": 2.0, "range": "2.00 - 2.49"},
        {"label": "Pass",               "min": 1.0, "range": "1.00 - 1.99"},
        {"label": "Fail",               "min": 0.0, "range": "below 1.00"},
    ],
    "diploma": [
        {"label": "Distinction", "min": 3.6, "range": "3.60 - 4.00"},
        {"label": "Credit",      "min": 2.5, "range": "2.50 - 3.59"},
        {"label": "Pass",        "min": 1.0, "range": "1.00 - 2.49"},
        {"label": "Fail",        "min": 0.0, "range": "below 1.00"},
    ],
}

# Below this CGPA a student is on academic probation (both award types)
PROBATION_THRESHOLD = 1.0

# ================================
# PROGRAMMES
# ================================

PROGRAMMES: list[dict] = [
    {"name": "Diploma in Accounting", "award_type": "diploma"},
    {"name": "Diploma in Marketing", "award_type": "diploma"},
    {"name": "Diploma in Management", "award_type": "diploma"},
    {"name": "Diploma in Public Relations", "award_type": "diploma"},
    {"name": "Diploma in Information Technology Management", "award_type": "diploma"},
    {"name": "Bachelor of Science in Data Science and Analytics", "award_type": "degree"},
    {"name": "Bachelor of Laws (LLB)", "award_type": "degree"},
    {"name": "Bachelor of Arts in Communication Studies", "award_type": "degree"},
    {"name": "Bachelor of Science in Logistics and Transport Management", "award_type": "degree"},
    {"name": "Bachelor of Arts in Public Relations Management", "award_type": "degree"},
    {"name": "Bachelor of Science in Accounting", "award_type": "degree"},
    {"name": "Bachelor of Science in Accounting and Finance", "award_type": "degree"},
    {"name": "Bachelor of Science in Business Economics", "award_type": "degree"},
    {"name": "Bachelor of Science in Actuarial Science", "award_type": "degree"},
    {"name": "Bachelor of Science in Banking and Finance", "award_type": "degree"},
    {"name": "Bachelor of Business Administration", "award_type": "degree"},
    {"name": "Bachelor of Science in Information Technology", "award_type": "degree"},
    {"name": "Bachelor of Science in Marketing", "award_type": "degree"},
    {"name": "Bachelor of Science in Real Estate Management and Finance", "award_type": "degree"},
]

MAX_LEVEL = {"diploma": 200, "degree": 400}


def award_type_for_programme(programme: str) -> AwardType:
    """Infers the award type from a programme name ("Diploma in …" → diploma)."""
    return "diploma" if programme.strip().lower().startswith("diploma") else "degree"


def is_diploma_course_code(code: str) -> bool:
    """UPSA diploma course codes start with DIP (DIPC, DIPT, DIPL, …)."""
    return code.strip().upper().startswith("DIP")


# ================================
# GRADES / GPA
# ================================

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


def truncate_gpa(total_points: float, total_credits: float) -> float:
    """
    Divides points by credits and truncates to 2 decimal places.
    UPSA truncates rather than rounds (56.5 / 20 = 2.825 is reported as 2.82),
    so a GPA is never shown higher than the university would report it.
    """
    if not total_credits:
        return 0.0
    value = Decimal(str(total_points)) / Decimal(str(total_credits))
    return float(value.quantize(Decimal("0.01"), rounding=ROUND_DOWN))


def get_classification(cgpa: float, award_type: AwardType = "degree") -> str:
    """Returns the classification label for a CGPA under the given award type."""
    for band in CLASSIFICATION_BANDS[award_type]:
        if cgpa >= band["min"]:
            return band["label"]
    return "Fail"


def get_next_band(cgpa: float, award_type: AwardType = "degree") -> Optional[dict]:
    """Returns the next band above the student's current one, or None at the top."""
    bands = CLASSIFICATION_BANDS[award_type]
    for i, band in enumerate(bands):
        if cgpa >= band["min"]:
            return bands[i - 1] if i > 0 else None
    return None


def get_academic_standing(cgpa: float) -> str:
    """
    Returns academic standing based on CGPA.
    Probation threshold is below 1.0 per UPSA policy.
    """
    if cgpa < PROBATION_THRESHOLD:
        return "Probation"
    return "Good Standing"


# ================================
# ACADEMIC YEARS
# ================================

ACADEMIC_YEAR_PATTERN = re.compile(r"^(\d{4})/(\d{4})$")


def parse_academic_year(value: str) -> int:
    """
    Returns the starting calendar year of an academic year string.
    "2024/2025" → 2024. Raises ValueError for anything else.
    """
    match = ACADEMIC_YEAR_PATTERN.match(value.strip())
    if not match or int(match.group(2)) != int(match.group(1)) + 1:
        raise ValueError("Academic year must be in format YYYY/YYYY e.g. 2024/2025")
    return int(match.group(1))


def format_academic_year(start_year: int) -> str:
    return f"{start_year}/{start_year + 1}"


def current_academic_year(today: Optional[date] = None) -> str:
    """UPSA's academic year starts in August."""
    today = today or date.today()
    start = today.year if today.month >= 8 else today.year - 1
    return format_academic_year(start)


def selectable_academic_years(today: Optional[date] = None, back: int = 8) -> list[str]:
    """Academic years a student may pick, newest first."""
    start = parse_academic_year(current_academic_year(today))
    return [format_academic_year(y) for y in range(start, start - back - 1, -1)]


def level_for_academic_year(entry_level: int, start_academic_year: str, academic_year: str) -> int:
    """
    Level a semester belongs to, counted from the programme's entry level.
    A top-up entering at 300 in 2026/2027 is Level 300 in 2026/2027 and 400 in 2027/2028.
    """
    offset = parse_academic_year(academic_year) - parse_academic_year(start_academic_year)
    return entry_level + 100 * max(offset, 0)
