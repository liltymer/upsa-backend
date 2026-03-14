from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.database import Base


class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)

    # Course details
    code = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    credit_hours = Column(Integer, nullable=False)
    programme = Column(String, nullable=True)  # optional — which programme this belongs to
    level = Column(Integer, nullable=True)     # optional — which level this course is for