from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.course import Course
from app.models.student import Student
from app.schemas.course import CourseCreate, CourseResponse
from app.services.auth import require_admin

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

    course = Course(**payload.model_dump(exclude={"code"}), code=code)

    db.add(course)
    db.commit()
    db.refresh(course)

    return course


@router.get("/", response_model=list[CourseResponse])
def list_courses(db: Session = Depends(get_db)):
    return db.query(Course).order_by(Course.code).all()
