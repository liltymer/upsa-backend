from pydantic import BaseModel


class ProjectedCourse(BaseModel):
    credit_hours: int
    grade_point: float