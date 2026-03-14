from pydantic import BaseModel
from typing import List


class CourseRecord(BaseModel):
    course_code: str
    course_title: str
    credits: int
    grade: str
    grade_point: float


class SemesterTranscript(BaseModel):
    year: int
    semester: int
    courses: List[CourseRecord]
    semester_gpa: float


class TranscriptResponse(BaseModel):
    student_name: str
    index_number: str
    programme: str
    level: int
    academic_year: str
    transcript: List[SemesterTranscript]
    cgpa: float