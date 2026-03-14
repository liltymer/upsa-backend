from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.database import Base


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)

    # Personal info
    name = Column(String, nullable=False)
    index_number = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)

    # Academic info
    programme = Column(String, nullable=False)
    level = Column(Integer, nullable=False)          # 100, 200, 300, 400
    academic_year = Column(String, nullable=False)   # e.g. "2024/2025"

    # Role
    role = Column(String, default="student")

    results = relationship(
        "Result",
        back_populates="student",
        cascade="all, delete",
        passive_deletes=True
    )