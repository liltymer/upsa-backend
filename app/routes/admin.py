from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import func
from typing import List

from app.database import get_db
from app.models.student import Student
from app.models.result import Result
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.announcement import Announcement
from app.models.password_reset import PasswordResetToken
from app.schemas.announcement import (
    AnnouncementCreate,
    AnnouncementUpdate,
    AnnouncementResponse,
)
from app.schemas.course import CourseCreate
from app.services.auth import require_admin
from app.utils.grading import CLASSIFICATION_BANDS, get_classification, truncate_gpa

router = APIRouter(prefix="/admin", tags=["admin"])


# ================================
# PLATFORM STATS
# ================================

def _current_enrollments(db: Session):
    return (
        db.query(Enrollment)
        .join(Student, Student.id == Enrollment.student_id)
        .filter(Student.role == "student", Enrollment.is_current.is_(True))
    )


@router.get("/stats")
def get_platform_stats(
    db: Session = Depends(get_db),
    admin: Student = Depends(require_admin),
):
    total_students = db.query(Student).filter(Student.role == "student").count()
    active_users = db.query(Result.student_id).distinct().count()
    total_results = db.query(Result).count()
    total_announcements = db.query(Announcement).filter(
        Announcement.is_active.is_(True)
    ).count()

    # Students with more than one programme (e.g. diploma → degree top-up)
    top_up_students = (
        db.query(Enrollment.student_id)
        .group_by(Enrollment.student_id)
        .having(func.count(Enrollment.id) > 1)
        .count()
    )

    current = _current_enrollments(db).subquery()
    programme_stats = (
        db.query(current.c.programme, func.count(current.c.id))
        .group_by(current.c.programme)
        .all()
    )
    level_stats = (
        db.query(current.c.current_level, func.count(current.c.id))
        .group_by(current.c.current_level)
        .order_by(current.c.current_level)
        .all()
    )

    return {
        "total_students": total_students,
        "active_users": active_users,
        "total_results": total_results,
        "active_announcements": total_announcements,
        "top_up_students": top_up_students,
        "programme_distribution": [
            {"programme": p, "count": c}
            for p, c in programme_stats
        ],
        "level_distribution": [
            {"level": lvl, "count": c}
            for lvl, c in level_stats
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
        .options(selectinload(Student.enrollments))
        .filter(Student.role == "student")
        .order_by(Student.id.desc())
        .all()
    )

    users = []
    for s in students:
        current = s.current_enrollment
        users.append({
            "id": s.id,
            "name": s.name,
            "email": s.email,
            "index_number": current.index_number if current else None,
            "programme": current.programme if current else None,
            "level": current.current_level if current else None,
            "academic_year": current.start_academic_year if current else None,
            "programmes": [
                {
                    "index_number": e.index_number,
                    "programme": e.programme,
                    "award_type": e.award_type,
                    "status": e.status,
                    "is_current": e.is_current,
                }
                for e in s.enrollments
            ],
            # NO grades, NO results, NO CGPA
        })

    return {"total": len(users), "students": users}


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
        raise HTTPException(status_code=404, detail="Student not found.")

    name = student.name

    # Remove dependent rows explicitly so this works on every database backend
    db.query(PasswordResetToken).filter(PasswordResetToken.student_id == student_id).delete()
    db.query(Result).filter(Result.student_id == student_id).delete()
    db.query(Enrollment).filter(Enrollment.student_id == student_id).delete()
    db.expire(student)
    db.delete(student)
    db.commit()

    return {"message": f"Student {name} deleted successfully."}


# ================================
# ANONYMOUS ANALYTICS
# ================================

@router.get("/analytics")
def get_anonymous_analytics(
    db: Session = Depends(get_db),
    admin: Student = Depends(require_admin),
):
    """
    Classification and risk counts over each student's CURRENT programme.
    Diploma and degree classes are counted separately (Distinction/Credit vs First Class …).
    """
    enrollments = _current_enrollments(db).all()

    # One grouped query instead of one query per student
    totals_by_enrollment = {
        eid: (points or 0.0, credits or 0)
        for eid, points, credits in (
            db.query(
                Result.enrollment_id,
                func.sum(Result.grade_point * Result.credit_hours),
                func.sum(Result.credit_hours),
            )
            .group_by(Result.enrollment_id)
            .all()
        )
    }

    classifications = {"degree": {}, "diploma": {}}
    for award_type, bands in CLASSIFICATION_BANDS.items():
        classifications[award_type] = {band["label"]: 0 for band in bands}
        classifications[award_type]["No Data"] = 0

    risk_levels = {"Low": 0, "Medium": 0, "High": 0, "No Data": 0}
    cgpa_values = []

    for e in enrollments:
        points, credits = totals_by_enrollment.get(e.id, (0.0, 0))
        if not credits:
            classifications[e.award_type]["No Data"] += 1
            risk_levels["No Data"] += 1
            continue

        cgpa = truncate_gpa(points, credits)
        cgpa_values.append(cgpa)
        label = get_classification(cgpa, e.award_type)
        classifications[e.award_type][label] += 1

        if cgpa >= 3.0:
            risk_levels["Low"] += 1
        elif cgpa >= 2.0 and label != "Pass":
            risk_levels["Medium"] += 1
        else:
            risk_levels["High"] += 1

    # Combined view for existing dashboard widgets
    combined = {}
    for per_type in classifications.values():
        for label, count in per_type.items():
            combined[label] = combined.get(label, 0) + count

    return {
        "total_analysed": len(enrollments),
        "average_cgpa": truncate_gpa(sum(cgpa_values), len(cgpa_values)) if cgpa_values else 0,
        "classification_distribution": combined,
        "classification_by_award_type": classifications,
        "risk_distribution": risk_levels,
    }


# ================================
# ANNOUNCEMENTS: ADMIN CRUD
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
# COURSE CATALOGUE: ADMIN CRUD
# ================================

@router.get("/courses")
def get_all_courses(
    db: Session = Depends(get_db),
    admin: Student = Depends(require_admin),
):
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


@router.post("/courses", status_code=status.HTTP_201_CREATED)
def create_course(
    data: CourseCreate,
    db: Session = Depends(get_db),
    admin: Student = Depends(require_admin),
):
    code = data.code.upper().strip()

    if db.query(Course).filter(Course.code == code).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Course {code} already exists."
        )

    course = Course(
        code=code,
        name=data.name.strip(),
        credit_hours=data.credit_hours,
        programme=data.programme,
        level=data.level,
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
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found.")
    db.delete(course)
    db.commit()
    return {"message": "Course deleted."}