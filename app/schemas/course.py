from pydantic import BaseModel
from typing import Optional


class CourseCreate(BaseModel):
    code: str
    name: str
    credit_hours: int
    programme: Optional[str] = None
    level: Optional[int] = None


class CourseResponse(BaseModel):
    id: int
    code: str
    name: str
    credit_hours: int
    programme: Optional[str] = None
    level: Optional[int] = None

    class Config:
        from_attributes = True