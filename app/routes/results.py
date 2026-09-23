from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.enrollment import Enrollment
from app.models.result import Result
from app.models.student import Student
from app.services.auth import get_current_user
from app.services.enrollments import get_enrollment, summarize_enrollment
from app.utils.gpa import semester_summaries
from app.utils.grading import (
    VALID_GRADES,
    current_academic_year,
    grade_to_point,
    level_for_academic_year,
    parse_academic_year,
)

router = APIRouter(prefix="/results", tags=["Results"])


# ================================
# REQUEST SCHEMAS
# ================================

class ResultCreate(BaseModel):
    course_code: str = Field(min_length=1, max_length=20)
    course_name: str = Field(min_length=1, max_length=200)
    credit_hours: int = Field(ge=1, le=12)
    grade: str
    academic_year: str = Field(description='e.g. "2024/2025"')
    semester: Literal[1, 2]
    enrollment_id: Optional[int] = Field(None, description="Defaults to the current programme")


class ResultUpdate(BaseModel):
    """Every field is optional: results in completed programmes can still be corrected."""
    grade: Optional[str] = None
    course_code: Optional[str] = Field(None, min_length=1, max_length=20)
    course_name: Optional[str] = Field(None, min_length=1, max_length=200)
    credit_hours: Optional[int] = Field(None, ge=1, le=12)
    academic_year: Optional[str] = None
    semester: Optional[Literal[1, 2]] = None


class ResultMove(BaseModel):
    result_ids: list[int] = Field(min_length=1, max_length=200)
    enrollment_id: int


# ================================
# HELPERS
# ================================

def normalize_grade(grade: str) -> str:
    grade = grade.strip().upper()
    if grade not in VALID_GRADES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid grade '{grade}'. Valid grades are: {', '.join(VALID_GRADES)}",
        )
    return grade


def validate_academic_year(enrollment: Enrollment, academic_year: str) -> str:
    """The semester must fall between the programme's start and the current academic year."""
    academic_year = academic_year.strip()
    try:
        year = parse_academic_year(academic_year)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if year < parse_academic_year(enrollment.start_academic_year):
        raise HTTPException(
            status_code=400,
            detail=f"{academic_year} is before {enrollment.programme} started "
                   f"({enrollment.start_academic_year}). Check the academic year, or update the programme's start year.",
        )
    if year > parse_academic_year(current_academic_year()):
        raise HTTPException(status_code=400, detail=f"{academic_year} has not started yet.")
    return academic_year


def get_own_result(result_id: int, current_user: Student, db: Session) -> Result:
    """Fetches a result owned by the current user; 404 otherwise so ids cannot be probed."""
    result = db.query(Result).filter(
        Result.id == result_id,
        Result.student_id == current_user.id,
    ).first()
    if not result:
        raise HTTPException(status_code=404, detail="Result not found.")
    return result


def ensure_not_duplicate(db: Session, result: Result) -> None:
    clash = db.query(Result).filter(
        Result.enrollment_id == result.enrollment_id,
        Result.course_code == result.course_code,
        Result.academic_year == result.academic_year,
        Result.semester == result.semester,
        Result.id != result.id,
    ).first()
    if clash:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{result.course_code} already exists for {result.academic_year} "
                   f"Semester {result.semester}. Edit the existing entry instead.",
        )


def serialize(result: Result, enrollment: Enrollment) -> dict:
    return {
        "result_id": result.id,
        "enrollment_id": result.enrollment_id,
        "course_code": result.course_code,
        "course_name": result.course_name,
        "credit_hours": result.credit_hours,
        "grade": result.grade,
        "grade_point": result.grade_point,
        "grade_value": result.grade_point * result.credit_hours,
        "academic_year": result.academic_year,
        "semester": result.semester,
        "level": level_for_academic_year(
            enrollment.entry_level, enrollment.start_academic_year, result.academic_year
        ),
    }


# ================================
# ADD RESULT
# ================================

@router.post("/", status_code=status.HTTP_201_CREATED)
def create_result(
    payload: ResultCreate,
    db: Session = Depends(get_db),
    current_user: Student = Depends(get_current_user),
):
    """
    Student adds a result exactly as printed on their result slip / transcript.
    Grade point is derived from the grade.
    """
    enrollment = get_enrollment(payload.enrollment_id, db, current_user)
    grade = normalize_grade(payload.grade)

    result = Result(
        student_id=current_user.id,
        enrollment_id=enrollment.id,
        course_code=payload.course_code.strip().upper(),
        course_name=payload.course_name.strip(),
        credit_hours=payload.credit_hours,
        grade=grade,
        grade_point=grade_to_point(grade),
        academic_year=validate_academic_year(enrollment, payload.academic_year),
        semester=payload.semester,
    )
    ensure_not_duplicate(db, result)

    db.add(result)
    db.commit()
    db.refresh(result)

    return {"message": "Result added successfully.", **serialize(result, enrollment)}


# ================================
# GET MY RESULTS
# ================================

@router.get("/me")
def get_my_results(
    db: Session = Depends(get_db),
    current_user: Student = Depends(get_current_user),
    enrollment: Enrollment = Depends(get_enrollment),
):
    """
    Results for one programme (current by default), grouped by semester in
    transcript order with each semester's GPA and running CGPA.
    """
    results = (
        db.query(Result)
        .filter(Result.enrollment_id == enrollment.id)
        .order_by(Result.academic_year, Result.semester, Result.course_code)
        .all()
    )

    semesters = [
        {
            "academic_year": s["academic_year"],
            "semester": s["semester"],
            "level": level_for_academic_year(
                enrollment.entry_level, enrollment.start_academic_year, s["academic_year"]
            ),
            "total_credits": s["total_credits"],
            "total_grade_points": s["total_grade_points"],
            "gpa": s["gpa"],
            "cgpa": s["cgpa"],
            "results": [serialize(r, enrollment) for r in s["results"]],
        }
        for s in semester_summaries(results)
    ]

    return {
        "student": current_user.name,
        "enrollment": summarize_enrollment(db, enrollment),
        "programme": enrollment.programme,
        "level": enrollment.current_level,
        "total_results": len(results),
        "semesters": semesters,
        "results": [serialize(r, enrollment) for r in results],
    }


# ================================
# UPDATE RESULT
# ================================

@router.put("/{result_id}")
def update_result(
    result_id: int,
    payload: ResultUpdate,
    db: Session = Depends(get_db),
    current_user: Student = Depends(get_current_user),
):
    """
    Correct a previously entered result. Allowed in completed programmes too,
    so typos on a finished diploma can still be fixed.
    """
    result = get_own_result(result_id, current_user, db)
    enrollment = result.enrollment
    previous = {"grade": result.grade, "grade_point": result.grade_point}

    if payload.grade is not None:
        result.grade = normalize_grade(payload.grade)
        result.grade_point = grade_to_point(result.grade)
    if payload.course_code is not None:
        result.course_code = payload.course_code.strip().upper()
    if payload.course_name is not None:
        result.course_name = payload.course_name.strip()
    if payload.credit_hours is not None:
        result.credit_hours = payload.credit_hours
    if payload.academic_year is not None:
        result.academic_year = validate_academic_year(enrollment, payload.academic_year)
    if payload.semester is not None:
        result.semester = payload.semester

    ensure_not_duplicate(db, result)
    db.commit()
    db.refresh(result)

    return {
        "message": "Result updated successfully.",
        "previous_grade": previous["grade"],
        "previous_grade_point": previous["grade_point"],
        "new_grade": result.grade,
        "new_grade_point": result.grade_point,
        **serialize(result, enrollment),
    }


# ================================
# MOVE RESULTS BETWEEN PROGRAMMES
# ================================

@router.post("/move")
def move_results(
    payload: ResultMove,
    db: Session = Depends(get_db),
    current_user: Student = Depends(get_current_user),
):
    """
    Move results to another of the student's programmes: used to separate
    diploma results that were entered under a degree (or vice versa).
    """
    target = get_enrollment(payload.enrollment_id, db, current_user)
    results = db.query(Result).filter(
        Result.id.in_(payload.result_ids),
        Result.student_id == current_user.id,
    ).all()

    if len(results) != len(set(payload.result_ids)):
        raise HTTPException(status_code=404, detail="One or more results were not found.")

    for result in results:
        result.enrollment_id = target.id
        if result.academic_year < target.start_academic_year:
            # Keep the programme's start consistent with its earliest semester
            target.start_academic_year = result.academic_year
    db.flush()
    for result in results:
        ensure_not_duplicate(db, result)

    db.commit()
    return {
        "message": f"Moved {len(results)} result{'s' if len(results) != 1 else ''} to {target.programme}.",
        "enrollment": summarize_enrollment(db, target),
    }


# ================================
# DELETE RESULT
# ================================

@router.delete("/{result_id}")
def delete_result(
    result_id: int,
    db: Session = Depends(get_db),
    current_user: Student = Depends(get_current_user),
):
    """Student removes a result they entered by mistake."""
    result = get_own_result(result_id, current_user, db)
    label = f"{result.course_code} {result.course_name} ({result.academic_year} Semester {result.semester})"

    db.delete(result)
    db.commit()

    return {"message": f"{label} deleted successfully."}
