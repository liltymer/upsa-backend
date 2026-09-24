from sqlalchemy import Column, DateTime, Integer, String, func
from sqlalchemy.orm import relationship

from app.database import Base


class Student(Base):
    """
    A person's login account. Academic details (index number, programme,
    level) live on their enrollments: see app/models/enrollment.py.
    """
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)

    # Personal info
    name = Column(String, nullable=False)
    # What the student wants to be called in greetings (names are ordered differently)
    preferred_name = Column(String(60), nullable=True)
    email = Column(String, unique=True, nullable=False, index=True)
    # When the account was made and when it last signed in (admin activity figures)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    password_hash = Column(String, nullable=False)

    # Role
    role = Column(String, nullable=False, default="student")

    enrollments = relationship(
        "Enrollment",
        back_populates="student",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Enrollment.start_academic_year",
    )

    results = relationship(
        "Result",
        back_populates="student",
        cascade="all, delete",
        passive_deletes=True,
    )

    @property
    def current_enrollment(self):
        return next((e for e in self.enrollments if e.is_current), None)
