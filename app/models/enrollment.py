from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Enrollment(Base):
    """
    One programme a student is (or was) registered on at UPSA.

    A student who tops up from a diploma to a degree has two enrollments:
    the completed diploma (old index number, its own final CGPA) and the
    active degree (new index number, fresh CGPA). GPA figures are always
    computed per enrollment: never across them.
    """
    __tablename__ = "enrollments"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(
        Integer, ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    # Nullable only for a previous programme the migration split out whose index is unknown
    index_number = Column(String(30), unique=True, nullable=True, index=True)
    programme = Column(String(200), nullable=False)
    award_type = Column(String(20), nullable=False)             # diploma | degree
    entry_level = Column(Integer, nullable=False)                # 100, or 300 for a top-up
    current_level = Column(Integer, nullable=False)              # 100 - 400
    start_academic_year = Column(String(9), nullable=False)      # e.g. "2024/2025"

    status = Column(String(20), nullable=False, default="active")  # active | completed
    is_current = Column(Boolean, nullable=False, default=True)
    # Set when the system created/split this record and the student should confirm the details
    needs_review = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    student = relationship("Student", back_populates="enrollments")
    results = relationship(
        "Result",
        back_populates="enrollment",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
