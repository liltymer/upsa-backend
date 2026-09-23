from typing import Literal, Optional

from pydantic import BaseModel, Field

AwardType = Literal["diploma", "degree"]


class PreviousProgramme(BaseModel):
    """A programme the student already completed, e.g. their diploma before a top-up."""
    index_number: Optional[str] = Field(None, max_length=30)
    programme: str = Field(min_length=2, max_length=200)
    start_academic_year: str = Field(description='e.g. "2024/2025"')


class TopUpRequest(BaseModel):
    index_number: str = Field(min_length=1, max_length=30)
    programme: str = Field(min_length=2, max_length=200)
    academic_year: str = Field(description="Academic year the top-up started, e.g. 2026/2027")
    entry_level: Literal[200, 300] = 300


class EnrollmentUpdate(BaseModel):
    """Corrections to a programme record (typos, wrong level, missing index number)."""
    index_number: Optional[str] = Field(None, min_length=1, max_length=30)
    programme: Optional[str] = Field(None, min_length=2, max_length=200)
    current_level: Optional[Literal[100, 200, 300, 400]] = None
    entry_level: Optional[Literal[100, 200, 300, 400]] = None
    start_academic_year: Optional[str] = None
    status: Optional[Literal["active", "completed"]] = None


class LinkAccountRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)


class AreaLabel(BaseModel):
    code: str = Field(min_length=1, max_length=12, pattern=r"^[A-Za-z]+$")
    # Empty name resets the area to its default name
    name: str = Field("", max_length=40)
