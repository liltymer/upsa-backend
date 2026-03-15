from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from datetime import datetime, timedelta

from app.database import get_db
from app.models.student import Student
from app.models.result import Result
from app.models.announcement import Announcement
from app.schemas.announcement import (
    AnnouncementCreate,
    AnnouncementUpdate,
    AnnouncementResponse,
)
from app.services.auth import get_current_user

router = APIRouter(prefix="/admin", tags=["admin"])


# ================================
# ADMIN GUARD
# ================================

def require_admin(current_user: Student = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required."
        )
    return current_user


# ================================
# PLATFORM STATS
# ================================

@router.get("/stats")
def get_platform_stats(
    db: Session = Depends(get_db),
    admin: Student = Depends(require_admin),
):
    total_students = db.query(Student).filter(
        Student.role == "student"
    ).count()

    today = datetime.utcnow().date()
    week_ago = datetime.utcnow() - timedelta(days=7)
    month_ago = datetime.utcnow() - timedelta(days=30)

    # Students with results (active users)
    active_users = db.query(Result.student_id).distinct().count()

    # Total results entered
    total_results = db.query(Result).count()

    # Total announcements
    total_announcements = db.query(Announcement).filter(
        Announcement.is_active == True
    ).count()

    # Programme distribution
    programme_stats = (
        db.query(Student.programme, func.count(Student.id).label("count"))
        .filter(Student.role == "student")
        .group_by(Student.programme)
        .all()
    )

    # Level distribution
    level_stats = (
        db.query(Student.level, func.count(Student.id).label("count"))
        .filter(Student.role == "student")
        .group_by(Student.level)
        .order_by(Student.level)
        .all()
    )

    return {
        "total_students": total_students,
        "active_users": active_users,
        "total_results": total_results,
        "active_announcements": total_announcements,
        "programme_distribution": [
            {"programme": p, "count": c}
            for p, c in programme_stats
        ],
        "level_distribution": [
            {"level": l, "count": c}
            for l, c in level_stats
        ],
    }


# ================================
# USER LIST
# ================================

@router.get("/users")
def get_all_users(
    db: Session = Depends(get_db),
    admin: Student = Depends(require_admin),
):
    students = (
        db.query(Student)
        .filter(Student.role == "student")
        .order_by(Student.id.desc())
        .all()
    )

    return {
        "total": len(students),
        "students": [
            {
                "id": s.id,
                "name": s.name,
                "index_number": s.index_number,
                "email": s.email,
                "programme": s.programme,
                "level": s.level,
                "academic_year": s.academic_year,
                # NO grades, NO results, NO CGPA
            }
            for s in students
        ],
    }


# ================================
# DELETE USER
# ================================

@router.delete("/users/{student_id}")
def delete_user(
    student_id: int,
    db: Session = Depends(get_db),
    admin: Student = Depends(require_admin),
):
    student = db.query(Student).filter(
        Student.id == student_id,
        Student.role == "student",
    ).first()

    if not student:
        raise HTTPException(
            status_code=404,
            detail="Student not found."
        )

    # Delete their results first
    db.query(Result).filter(Result.student_id == student_id).delete()
    db.delete(student)
    db.commit()

    return {"message": f"Student {student.name} deleted successfully."}


# ================================
# ANONYMOUS ANALYTICS
# ================================

@router.get("/analytics")
def get_anonymous_analytics(
    db: Session = Depends(get_db),
    admin: Student = Depends(require_admin),
):
    from app.utils.gpa import calculate_cgpa

    students = db.query(Student).filter(
        Student.role == "student"
    ).all()

    if not students:
        return {
            "total_analysed": 0,
            "classification_distribution": {},
            "risk_distribution": {},
            "average_cgpa": 0,
        }

    classifications = {
        "First Class": 0,
        "Second Class Upper": 0,
        "Second Class Lower": 0,
        "Third Class": 0,
        "Pass": 0,
        "Fail": 0,
        "No Data": 0,
    }

    risk_levels = {"Low": 0, "Medium": 0, "High": 0, "No Data": 0}
    cgpa_values = []

    for student in students:
        cgpa = calculate_cgpa(db, student.id)

        if cgpa == 0.0:
            classifications["No Data"] += 1
            risk_levels["No Data"] += 1
            continue

        cgpa_values.append(cgpa)

        # Classification
        if cgpa >= 3.6:
            classifications["First Class"] += 1
        elif cgpa >= 3.0:
            classifications["Second Class Upper"] += 1
        elif cgpa >= 2.5:
            classifications["Second Class Lower"] += 1
        elif cgpa >= 2.0:
            classifications["Third Class"] += 1
        elif cgpa >= 1.0:
            classifications["Pass"] += 1
        else:
            classifications["Fail"] += 1

        # Risk
        if cgpa >= 3.0:
            risk_levels["Low"] += 1
        elif cgpa >= 2.5:
            risk_levels["Medium"] += 1
        else:
            risk_levels["High"] += 1

    avg_cgpa = round(sum(cgpa_values) / len(cgpa_values), 2) if cgpa_values else 0

    return {
        "total_analysed": len(students),
        "average_cgpa": avg_cgpa,
        "classification_distribution": classifications,
        "risk_distribution": risk_levels,
    }


# ================================
# ANNOUNCEMENTS — ADMIN CRUD
# ================================

@router.get("/announcements", response_model=List[AnnouncementResponse])
def get_all_announcements(
    db: Session = Depends(get_db),
    admin: Student = Depends(require_admin),
):
    return db.query(Announcement).order_by(
        Announcement.created_at.desc()
    ).all()


@router.post("/announcements", response_model=AnnouncementResponse)
def create_announcement(
    data: AnnouncementCreate,
    db: Session = Depends(get_db),
    admin: Student = Depends(require_admin),
):
    announcement = Announcement(
        title=data.title,
        message=data.message,
        priority=data.priority,
        is_active=data.is_active,
    )
    db.add(announcement)
    db.commit()
    db.refresh(announcement)
    return announcement


@router.put("/announcements/{announcement_id}", response_model=AnnouncementResponse)
def update_announcement(
    announcement_id: int,
    data: AnnouncementUpdate,
    db: Session = Depends(get_db),
    admin: Student = Depends(require_admin),
):
    announcement = db.query(Announcement).filter(
        Announcement.id == announcement_id
    ).first()

    if not announcement:
        raise HTTPException(status_code=404, detail="Announcement not found.")

    if data.title is not None:
        announcement.title = data.title
    if data.message is not None:
        announcement.message = data.message
    if data.priority is not None:
        announcement.priority = data.priority
    if data.is_active is not None:
        announcement.is_active = data.is_active

    db.commit()
    db.refresh(announcement)
    return announcement


@router.delete("/announcements/{announcement_id}")
def delete_announcement(
    announcement_id: int,
    db: Session = Depends(get_db),
    admin: Student = Depends(require_admin),
):
    announcement = db.query(Announcement).filter(
        Announcement.id == announcement_id
    ).first()

    if not announcement:
        raise HTTPException(status_code=404, detail="Announcement not found.")

    db.delete(announcement)
    db.commit()
    return {"message": "Announcement deleted."}


# ================================
# COURSE CATALOGUE — ADMIN CRUD
# ================================

@router.get("/courses")
def get_all_courses(
    db: Session = Depends(get_db),
    admin: Student = Depends(require_admin),
):
    from app.models.course import Course
    courses = db.query(Course).order_by(Course.code).all()
    return {
        "total": len(courses),
        "courses": [
            {
                "id": c.id,
                "code": c.code,
                "name": c.name,
                "credit_hours": c.credit_hours,
                "programme": c.programme,
                "level": c.level,
            }
            for c in courses
        ],
    }


@router.post("/courses")
def create_course(
    data: dict,
    db: Session = Depends(get_db),
    admin: Student = Depends(require_admin),
):
    from app.models.course import Course
    course = Course(
        code=data.get("code", "").upper().strip(),
        name=data.get("name", "").strip(),
        credit_hours=int(data.get("credit_hours", 3)),
        programme=data.get("programme"),
        level=data.get("level"),
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return {"message": "Course created.", "id": course.id}


@router.delete("/courses/{course_id}")
def delete_course(
    course_id: int,
    db: Session = Depends(get_db),
    admin: Student = Depends(require_admin),
):
    from app.models.course import Course
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found.")
    db.delete(course)
    db.commit()
    return {"message": "Course deleted."}