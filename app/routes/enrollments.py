from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.enrollment import Enrollment
from app.models.password_reset import PasswordResetToken
from app.models.result import Result
from app.models.student import Student
from app.routes.auth import normalize_index
from app.schemas.enrollment import (
    EnrollmentUpdate,
    LinkAccountRequest,
    PreviousProgramme,
    TopUpRequest,
)
from app.services.auth import get_current_user, verify_password
from app.services.enrollments import (
    index_number_taken,
    summarize_enrollment,
    validate_level,
)
from app.services.rate_limit import rate_limit
from app.utils.grading import (
    CLASSIFICATION_BANDS,
    GRADE_SCALE,
    MAX_LEVEL,
    PROGRAMMES,
    TOP_UP_ENTRY_LEVELS,
    award_type_for_programme,
    current_academic_year,
    parse_academic_year,
    selectable_academic_years,
)

router = APIRouter(tags=["Programmes"])


def _own_enrollment(db: Session, student: Student, enrollment_id: int) -> Enrollment:
    enrollment = db.query(Enrollment).filter(
        Enrollment.id == enrollment_id,
        Enrollment.student_id == student.id,
    ).first()
    if enrollment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Programme not found.")
    return enrollment


def _list(db: Session, student: Student) -> list[dict]:
    enrollments = (
        db.query(Enrollment)
        .filter(Enrollment.student_id == student.id)
        .order_by(Enrollment.is_current.desc(), Enrollment.start_academic_year.desc())
        .all()
    )
    return [summarize_enrollment(db, e) for e in enrollments]


# ================================
# REFERENCE DATA (public)
# ================================

@router.get("/reference/academic")
def academic_reference():
    """Programmes, academic years, grading scale and classification bands used by the app."""
    return {
        "programmes": PROGRAMMES,
        "academic_years": selectable_academic_years(),
        "current_academic_year": current_academic_year(),
        "grade_scale": GRADE_SCALE,
        "classification_bands": CLASSIFICATION_BANDS,
        "max_level": MAX_LEVEL,
        "top_up_entry_levels": TOP_UP_ENTRY_LEVELS,
    }


# ================================
# MY PROGRAMMES
# ================================

@router.get("/enrollments/me")
def my_enrollments(
    db: Session = Depends(get_db),
    current_user: Student = Depends(get_current_user),
):
    """Every programme on the account: current first, then previous ones."""
    return {"enrollments": _list(db, current_user)}


@router.post("/enrollments/top-up", status_code=status.HTTP_201_CREATED)
def start_top_up(
    data: TopUpRequest,
    db: Session = Depends(get_db),
    current_user: Student = Depends(get_current_user),
):
    """
    Start a new programme (typically a diploma → degree top-up) with its new
    index number. The previous programme is marked completed and keeps its
    results and final CGPA; the new programme starts with a fresh CGPA.
    """
    index_number = normalize_index(data.index_number)
    programme = data.programme.strip()
    award_type = award_type_for_programme(programme)

    try:
        parse_academic_year(data.academic_year)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    validate_level(award_type, data.entry_level, data.entry_level)

    if index_number_taken(db, index_number):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="That index number is already registered. If it is your other account, link it instead.",
        )

    for previous in current_user.enrollments:
        if previous.is_current:
            previous.is_current = False
            previous.status = "completed"

    db.add(Enrollment(
        student_id=current_user.id,
        index_number=index_number,
        programme=programme,
        award_type=award_type,
        entry_level=data.entry_level,
        current_level=data.entry_level,
        start_academic_year=data.academic_year.strip(),
        status="active",
        is_current=True,
    ))
    db.commit()

    return {
        "message": f"{programme} started. Your previous programme and its results are kept under Academic History.",
        "enrollments": _list(db, current_user),
    }


@router.post("/enrollments/previous", status_code=status.HTTP_201_CREATED)
def add_previous_programme(
    data: PreviousProgramme,
    db: Session = Depends(get_db),
    current_user: Student = Depends(get_current_user),
):
    """Record a programme the student already completed (e.g. the diploma before a top-up)."""
    try:
        parse_academic_year(data.start_academic_year)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    index_number = normalize_index(data.index_number) if data.index_number else None
    if index_number and index_number_taken(db, index_number):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="That index number is already registered. If it is your other account, link it instead.",
        )

    award_type = award_type_for_programme(data.programme)
    db.add(Enrollment(
        student_id=current_user.id,
        index_number=index_number,
        programme=data.programme.strip(),
        award_type=award_type,
        entry_level=100,
        current_level=MAX_LEVEL[award_type],
        start_academic_year=data.start_academic_year.strip(),
        status="completed",
        is_current=False,
    ))
    db.commit()
    return {"message": "Previous programme added.", "enrollments": _list(db, current_user)}


@router.patch("/enrollments/{enrollment_id}")
def update_enrollment(
    enrollment_id: int,
    data: EnrollmentUpdate,
    db: Session = Depends(get_db),
    current_user: Student = Depends(get_current_user),
):
    """Correct a programme record: works for completed programmes too (typo fixes)."""
    enrollment = _own_enrollment(db, current_user, enrollment_id)

    if data.index_number is not None:
        index_number = normalize_index(data.index_number)
        if index_number_taken(db, index_number, exclude_enrollment_id=enrollment.id):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="That index number is already registered.")
        enrollment.index_number = index_number

    if data.programme is not None:
        enrollment.programme = data.programme.strip()
        enrollment.award_type = award_type_for_programme(enrollment.programme)

    if data.start_academic_year is not None:
        try:
            parse_academic_year(data.start_academic_year)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        enrollment.start_academic_year = data.start_academic_year.strip()

    if data.entry_level is not None:
        enrollment.entry_level = data.entry_level
    if data.current_level is not None:
        enrollment.current_level = data.current_level
    enrollment.current_level = max(enrollment.current_level, enrollment.entry_level)
    validate_level(enrollment.award_type, enrollment.current_level, enrollment.entry_level)

    if data.status is not None and not enrollment.is_current:
        enrollment.status = data.status

    enrollment.needs_review = False
    db.commit()
    return {"message": "Programme updated.", "enrollment": summarize_enrollment(db, enrollment)}


@router.delete("/enrollments/{enrollment_id}")
def delete_enrollment(
    enrollment_id: int,
    db: Session = Depends(get_db),
    current_user: Student = Depends(get_current_user),
):
    """
    Remove a programme added by mistake. Only allowed when it has no results
    and it is not the only programme. Deleting the current programme makes
    the most recent remaining one current again (undo an accidental top-up).
    """
    enrollment = _own_enrollment(db, current_user, enrollment_id)

    if len(current_user.enrollments) <= 1:
        raise HTTPException(status_code=400, detail="You must keep at least one programme.")
    if db.query(Result).filter(Result.enrollment_id == enrollment.id).count():
        raise HTTPException(
            status_code=400,
            detail="This programme has results. Move or delete them first.",
        )

    was_current = enrollment.is_current
    db.delete(enrollment)
    db.flush()

    if was_current:
        latest = (
            db.query(Enrollment)
            .filter(Enrollment.student_id == current_user.id)
            .order_by(Enrollment.start_academic_year.desc(), Enrollment.id.desc())
            .first()
        )
        latest.is_current = True
        latest.status = "active"

    db.commit()
    db.refresh(current_user)
    return {"message": "Programme removed.", "enrollments": _list(db, current_user)}


# ================================
# LINK AN OLD ACCOUNT
# ================================

@router.post(
    "/enrollments/link-account",
    dependencies=[Depends(rate_limit("link-account", limit=5, window_seconds=900))],
)
def link_account(
    data: LinkAccountRequest,
    db: Session = Depends(get_db),
    current_user: Student = Depends(get_current_user),
):
    """
    For students who created a second account when they topped up.
    Proving ownership of the other account (its email + password) moves all of
    its programmes and results into this account, then deletes the old account.
    """
    other = db.query(Student).filter(func.lower(Student.email) == data.email.strip().lower()).first()

    if not verify_password(data.password, other.password_hash if other else None):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email or password for the other account is incorrect.")
    if other.id == current_user.id:
        raise HTTPException(status_code=400, detail="That is the account you are signed in to.")
    if other.role != "student":
        raise HTTPException(status_code=400, detail="Only student accounts can be linked.")

    this_start = current_user.current_enrollment.start_academic_year if current_user.current_enrollment else ""
    moved = 0
    for enrollment in list(other.enrollments):
        enrollment.student_id = current_user.id
        # Keep whichever programme started most recently as the current one
        if enrollment.is_current and enrollment.start_academic_year <= this_start:
            enrollment.is_current = False
            enrollment.status = "completed"
        moved += 1

    if any(e.is_current for e in other.enrollments):
        for mine in current_user.enrollments:
            if mine.is_current:
                mine.is_current = False
                mine.status = "completed"

    db.query(Result).filter(Result.student_id == other.id).update({Result.student_id: current_user.id})
    db.query(PasswordResetToken).filter(PasswordResetToken.student_id == other.id).delete()
    db.flush()
    db.expire(other)
    db.delete(other)
    db.commit()
    db.refresh(current_user)

    return {
        "message": f"Linked {moved} programme{'s' if moved != 1 else ''} from {data.email.strip().lower()}. "
                   "That account has been closed; sign in with this one from now on.",
        "enrollments": _list(db, current_user),
    }
