from sqlalchemy.orm import Session
from collections import defaultdict

from app.models.result import Result
from app.models.student import Student
from app.utils.gpa import calculate_semester_gpa, calculate_cgpa


def generate_transcript(db: Session, student_id: int) -> dict | None:
    """
    Builds a full academic transcript for a student,
    grouped by semester and sorted chronologically.
    """
    student = db.query(Student).filter(Student.id == student_id).first()

    if not student:
        return None

    results = (
        db.query(Result)
        .filter(Result.student_id == student_id)
        .order_by(Result.year, Result.semester)
        .all()
    )

    semesters = defaultdict(list)

    for r in results:
        key = (r.year, r.semester)
        semesters[key].append(r)

    transcript_data = []

    for (year, semester), records in sorted(semesters.items()):
        courses = []

        for r in records:
            courses.append({
                "course_code": r.course_code,       # ✅ directly on Result
                "course_title": r.course_name,      # ✅ directly on Result
                "credits": r.credit_hours,          # ✅ directly on Result
                "grade": r.grade,
                "grade_point": r.grade_point,
            })

        semester_gpa = calculate_semester_gpa(db, student_id, year, semester)

        transcript_data.append({
            "year": year,
            "semester": semester,
            "courses": courses,
            "semester_gpa": semester_gpa,
        })

    cgpa = calculate_cgpa(db, student_id)

    return {
        "student_name": student.name,
        "index_number": student.index_number,
        "programme": student.programme,
        "level": student.level,
        "academic_year": student.academic_year,
        "transcript": transcript_data,
        "cgpa": cgpa,
    }