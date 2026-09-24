from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship

from app.database import Base


class Result(Base):
    __tablename__ = "results"

    id = Column(Integer, primary_key=True, index=True)

    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    enrollment_id = Column(Integer, ForeignKey("enrollments.id", ondelete="CASCADE"), nullable=False, index=True)

    # Course details: entered directly by student, no foreign key to courses table
    course_code = Column(String, nullable=False)      # e.g. DIPC003
    course_name = Column(String, nullable=False)      # e.g. Business Management
    credit_hours = Column(Integer, nullable=False)    # e.g. 3

    # Semester info: matches the UPSA transcript ("2024/2025 Academic Year - First Semester")
    academic_year = Column(String(9), nullable=False)  # e.g. "2024/2025"
    semester = Column(Integer, nullable=False)          # 1 or 2

    # Grade: entered directly by student (no score)
    grade = Column(String, nullable=False)            # e.g. A, B+, B, B-, C+, C, C-, D, F
    grade_point = Column(Float, nullable=False)

    # When it was entered (not the semester it belongs to)
    created_at = Column(DateTime(timezone=True), server_default=func.now())       # derived from grade on save

    student = relationship("Student", back_populates="results")
    enrollment = relationship("Enrollment", back_populates="results")
