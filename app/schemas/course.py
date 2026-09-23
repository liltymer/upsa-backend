from pydantic import BaseModel, ConfigDict, Field
from typing import Optional


class CourseCreate(BaseModel):
    code: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=1, max_length=200)
    credit_hours: int = Field(ge=1, le=12)
    programme: Optional[str] = None
    level: Optional[int] = None


class CourseResponse(BaseModel):
    id: int
    code: str
    name: str
    credit_hours: int
    programme: Optional[str] = None
    level: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)