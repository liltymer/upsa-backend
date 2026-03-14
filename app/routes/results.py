from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models.result import Result
from app.models.student import Student
from app.services.auth import get_current_user
from app.utils.grading import grade_to_point, VALID_GRADES

router = APIRouter(prefix="/results", tags=["Results"])


# ================================
# REQUEST SCHEMAS
# ================================

class ResultCreate(BaseModel):
    course_code: str
    course_name: str
    credit_hours: int
    grade: str
    year: int
    semester: int


class ResultUpdate(BaseModel):
    grade: str


# ================================
# HELPERS
# ================================

def validate_result_input(
    grade: str = None,
    semester: int = None,
    year: int = None,
    credit_hours: int = None
):
    """
    Validates result input fields.
    Raises HTTPException for any invalid value.
    """
    if grade is not None:
        grade = grade.strip().upper()
        if grade not in VALID_GRADES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid grade '{grade}'. "
                       f"Valid grades are: {', '.join(VALID_GRADES)}"
            )

    if semester is not None and semester not in (1, 2):
        raise HTTPException(
            status_code=400,
            detail="Semester must be 1 or 2."
        )

    if year is not None and year < 1:
        raise HTTPException(
            status_code=400,
            detail="Year must be a positive number."
        )

    if credit_hours is not None and credit_hours < 1:
        raise HTTPException(
            status_code=400,
            detail="Credit hours must be at least 1."
        )


def get_own_result(
    result_id: int,
    current_user: Student,
    db: Session
) -> Result:
    """
    Fetches a result by ID and verifies ownership.
    Returns 404 if not found, 403 if not owned by current user.
    """
    result = db.query(Result).filter(Result.id == result_id).first()

    if not result:
        raise HTTPException(
            status_code=404,
            detail="Result not found."
        )

    if result.student_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to modify this result."
        )

    return result


# ================================
# ADD RESULT
# ================================

@router.post("/")
def create_result(
    payload: ResultCreate,
    db: Session = Depends(get_db),
    current_user: Student = Depends(get_current_user)
):
    """
    Student adds a result by entering course details and grade directly.
    No score required — grade is the primary input.
    Grade point is automatically derived from the grade.
    """

    # Normalize grade
    grade = payload.grade.strip().upper()

    # Validate all inputs
    validate_result_input(
        grade=grade,
        semester=payload.semester,
        year=payload.year,
        credit_hours=payload.credit_hours,
    )

    # Normalize course code
    course_code = payload.course_code.strip().upper()
    course_name = payload.course_name.strip()

    if not course_code:
        raise HTTPException(
            status_code=400,
            detail="Course code cannot be empty."
        )

    if not course_name:
        raise HTTPException(
            status_code=400,
            detail="Course name cannot be empty."
        )

    # Check for duplicate — same course code + year + semester
    existing = db.query(Result).filter(
        Result.student_id == current_user.id,
        Result.course_code == course_code,
        Result.year == payload.year,
        Result.semester == payload.semester,
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"{course_code} already exists for "
                   f"Year {payload.year} Semester {payload.semester}. "
                   f"Use the update endpoint to correct it."
        )

    # Derive grade point from grade
    grade_point = grade_to_point(grade)

    result = Result(
        student_id=current_user.id,
        course_code=course_code,
        course_name=course_name,
        credit_hours=payload.credit_hours,
        grade=grade,
        grade_point=grade_point,
        year=payload.year,
        semester=payload.semester,
    )

    db.add(result)
    db.commit()
    db.refresh(result)

    return {
        "message": "Result added successfully.",
        "result_id": result.id,
        "course_code": result.course_code,
        "course_name": result.course_name,
        "credit_hours": result.credit_hours,
        "grade": result.grade,
        "grade_point": result.grade_point,
        "year": result.year,
        "semester": result.semester,
    }


# ================================
# GET MY RESULTS
# ================================

@router.get("/me")
def get_my_results(
    db: Session = Depends(get_db),
    current_user: Student = Depends(get_current_user)
):
    """
    Returns all results for the authenticated student,
    ordered by year and semester.
    """

    results = (
        db.query(Result)
        .filter(Result.student_id == current_user.id)
        .order_by(Result.year, Result.semester)
        .all()
    )

    if not results:
        return {
            "message": "No results found. Start by adding your semester results.",
            "total_results": 0,
            "results": []
        }

    output = []
    for r in results:
        output.append({
            "result_id": r.id,
            "course_code": r.course_code,
            "course_name": r.course_name,
            "credit_hours": r.credit_hours,
            "grade": r.grade,
            "grade_point": r.grade_point,
            "year": r.year,
            "semester": r.semester,
        })

    return {
        "student": current_user.name,
        "programme": current_user.programme,
        "level": current_user.level,
        "total_results": len(output),
        "results": output,
    }


# ================================
# UPDATE RESULT
# ================================

@router.put("/{result_id}")
def update_result(
    result_id: int,
    payload: ResultUpdate,
    db: Session = Depends(get_db),
    current_user: Student = Depends(get_current_user)
):
    """
    Student corrects a previously entered grade.
    Grade point is automatically recalculated.
    Only the result owner can update it.
    """

    grade = payload.grade.strip().upper()
    validate_result_input(grade=grade)

    result = get_own_result(result_id, current_user, db)

    old_grade = result.grade
    old_grade_point = result.grade_point

    # Recalculate grade point from new grade
    new_grade_point = grade_to_point(grade)

    result.grade = grade
    result.grade_point = new_grade_point

    db.commit()
    db.refresh(result)

    return {
        "message": "Result updated successfully.",
        "result_id": result.id,
        "course_code": result.course_code,
        "course_name": result.course_name,
        "previous_grade": old_grade,
        "previous_grade_point": old_grade_point,
        "new_grade": result.grade,
        "new_grade_point": result.grade_point,
        "year": result.year,
        "semester": result.semester,
    }


# ================================
# DELETE RESULT
# ================================

@router.delete("/{result_id}")
def delete_result(
    result_id: int,
    db: Session = Depends(get_db),
    current_user: Student = Depends(get_current_user)
):
    """
    Student removes a result they entered by mistake.
    Only the result owner can delete it.
    """

    result = get_own_result(result_id, current_user, db)

    course_code = result.course_code
    course_name = result.course_name
    year = result.year
    semester = result.semester

    db.delete(result)
    db.commit()

    return {
        "message": f"{course_code} — {course_name} "
                   f"(Year {year} Semester {semester}) "
                   f"deleted successfully."
    }