from pydantic import BaseModel, EmailStr
from typing import Optional


class StudentCreate(BaseModel):
    name: str
    index_number: str
    email: EmailStr
    password: str
    programme: str
    level: int
    academic_year: str


class StudentResponse(BaseModel):
    id: int
    name: str
    index_number: str
    email: str
    programme: str
    level: int
    academic_year: str

    class Config:
        from_attributes = True


class StudentProfileUpdate(BaseModel):
    """
    Used if a student wants to update their profile details.
    All fields optional — only provided fields are updated.
    """
    name: Optional[str] = None
    programme: Optional[str] = None
    level: Optional[int] = None
    academic_year: Optional[str] = None