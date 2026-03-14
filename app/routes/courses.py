from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.course import Course
from app.schemas.course import CourseCreate, CourseResponse

router = APIRouter(prefix="/courses", tags=["Courses"])


@router.post("/", response_model=CourseResponse)
def create_course(payload: CourseCreate, db: Session = Depends(get_db)):

    existing = db.query(Course).filter(Course.code == payload.code).first()

    if existing:
        raise HTTPException(status_code=400, detail="Course already exists")

    course = Course(**payload.model_dump())

    db.add(course)
    db.commit()
    db.refresh(course)

    return course


@router.get("/", response_model=list[CourseResponse])
def list_courses(db: Session = Depends(get_db)):
    return db.query(Course).all()
