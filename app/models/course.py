from sqlalchemy import Boolean, Column, Integer, String, UniqueConstraint

from app.database import Base


class Course(Base):
    """A UPSA course: one title per course code."""
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)

    # Course details
    code = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    credit_hours = Column(Integer, nullable=False)
    programme = Column(String, nullable=True)  # optional: which programme this belongs to
    level = Column(Integer, nullable=True)     # optional: which level this course is for
    semester = Column(Integer, nullable=True)  # 1 or 2 when known
    # "timetable" when loaded from UPSA's published timetables (credits assumed), "admin" when entered by an admin
    source = Column(String(20), nullable=True)


class CourseOffering(Base):
    """
    A course a programme takes in a given level and semester. Used to pre-fill the
    add-a-semester form. `hidden` lets an admin stop a course being suggested,
    including one learned from students' entries.
    """
    __tablename__ = "course_offerings"
    __table_args__ = (UniqueConstraint("programme", "level", "semester", "course_code", name="uq_offering"),)

    id = Column(Integer, primary_key=True, index=True)
    programme = Column(String, nullable=False, index=True)
    level = Column(Integer, nullable=False)
    semester = Column(Integer, nullable=False)
    course_code = Column(String, nullable=False)
    source = Column(String(20), nullable=False, default="admin")
    hidden = Column(Boolean, nullable=False, default=False)
