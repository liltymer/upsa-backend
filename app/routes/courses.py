from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.student import Student
from app.schemas.course import CourseCreate, CourseResponse
from app.services.auth import get_current_user, require_admin
from app.services.course_suggestions import suggest_courses
from app.services.enrollments import get_enrollment
from app.utils.grading import parse_academic_year

router = APIRouter(prefix="/courses", tags=["Courses"])


@router.post("/", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
def create_course(
    payload: CourseCreate,
    db: Session = Depends(get_db),
    admin: Student = Depends(require_admin),
):
    code = payload.code.upper().strip()

    existing = db.query(Course).filter(Course.code == code).first()

    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Course already exists")

    course = Course(**payload.model_dump(exclude={"code"}), code=code, source="admin")

    db.add(course)
    db.commit()
    db.refresh(course)

    return course


@router.get("/", response_model=list[CourseResponse])
def list_courses(db: Session = Depends(get_db)):
    return db.query(Course).order_by(Course.code).all()


@router.get("/suggestions")
def course_suggestions(
    academic_year: str = Query(..., description='e.g. "2025/2026"'),
    semester: int = Query(..., ge=1, le=2),
    db: Session = Depends(get_db),
    current_user: Student = Depends(get_current_user),
    enrollment: Enrollment = Depends(get_enrollment),
):
    """Courses to pre-fill for one semester of the student's programme."""
    try:
        parse_academic_year(academic_year)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return suggest_courses(db, enrollment, academic_year.strip(), semester)
