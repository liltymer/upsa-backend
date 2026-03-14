from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.student import Student

router = APIRouter(prefix="/students", tags=["Students"])


@router.post("/")
def create_student(name: str, index_number: str, db: Session = Depends(get_db)):

    existing = db.query(Student).filter(
        Student.index_number == index_number
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Student already exists")

    student = Student(name=name, index_number=index_number)

    db.add(student)
    db.commit()
    db.refresh(student)

    return student
