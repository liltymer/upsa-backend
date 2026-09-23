from pydantic import BaseModel, Field


class ProjectedCourse(BaseModel):
    credit_hours: int = Field(ge=1, le=12)
    grade_point: float = Field(ge=0.0, le=4.0)


class SimulateRequest(BaseModel):
    projected_courses: list[ProjectedCourse] = Field(min_length=1, max_length=60)
