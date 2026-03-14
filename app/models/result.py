from sqlalchemy import Column, Integer, Float, ForeignKey, String
from sqlalchemy.orm import relationship
from app.database import Base


class Result(Base):
    __tablename__ = "results"

    id = Column(Integer, primary_key=True, index=True)

    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)

    # Course details — entered directly by student, no foreign key to courses table
    course_code = Column(String, nullable=False)      # e.g. DIPC003
    course_name = Column(String, nullable=False)      # e.g. Business Management
    credit_hours = Column(Integer, nullable=False)    # e.g. 3

    # Semester info
    year = Column(Integer, nullable=False)            # e.g. 1, 2, 3
    semester = Column(Integer, nullable=False)        # 1 or 2

    # Grade — entered directly by student (no score)
    grade = Column(String, nullable=False)            # e.g. A, B+, B, B-, C+, C, C-, D, F
    grade_point = Column(Float, nullable=False)       # derived from grade on save

    # Relationship
    student = relationship("Student", back_populates="results")