"""Courses added from UPSA timetables published in October 2026.

Revision ID: 0006_timetables_oct
Revises: 0005_activity
Create Date: 2026-10-06
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0006_timetables_oct"
down_revision: Union[str, Sequence[str], None] = "0005_activity"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# code, title, level, semester, programme. Credits are not printed on timetables, so 3 until confirmed.
NEW_COURSES = [
    ("BLAW205", "Law of Torts I", 200, 1, "Bachelor of Laws (LLB)"),
    ("BLAW221", "Commercial Law I", 200, 1, "Bachelor of Laws (LLB)"),
    ("BLAW228", "Private International Law II", 200, 2, "Bachelor of Laws (LLB)"),
    ("BLAW313", "Energy Law I", 300, 1, "Bachelor of Laws (LLB)"),
    ("BLAW321", "Administrative Law", 300, 1, "Bachelor of Laws (LLB)"),
    ("BLAW335", "Human Rights Law I", 300, 1, "Bachelor of Laws (LLB)"),
    ("BLAW413", "Laws of Natural Resources I", 400, 1, "Bachelor of Laws (LLB)"),
    ("BASC309", "Data Analytics", 300, 1, "Bachelor of Science in Actuarial Science"),
    ("BASC403", "Life Insurance", 400, 1, "Bachelor of Science in Actuarial Science"),
    ("DIPR001", "English Language", 100, 1, "Diploma in Public Relations"),
    ("DIPR003", "Communication Skills", 100, 1, "Diploma in Public Relations"),
    ("DIPR053", "Public Relations Research Methods", 200, 1, "Diploma in Public Relations"),
    ("DIPR057", "Corporate Social Responsibility", 200, 1, "Diploma in Public Relations"),
    ("DIPT059", "Essentials of IT Sourcing and Procurement", 200, 1, "Diploma in Information Technology Management")
]


def upgrade() -> None:
    conn = op.get_bind()
    have = {row[0] for row in conn.execute(sa.text("SELECT code FROM courses"))}
    offered = {tuple(row) for row in conn.execute(sa.text(
        "SELECT programme, level, semester, course_code FROM course_offerings"))}
    for code, name, level, semester, programme in NEW_COURSES:
        # Leave alone anything an admin already added or corrected
        if code not in have:
            conn.execute(sa.text(
                "INSERT INTO courses (code, name, credit_hours, level, semester, source) "
                "VALUES (:code, :name, 3, :level, :semester, 'timetable')"
            ), {"code": code, "name": name, "level": level, "semester": semester})
        if (programme, level, semester, code) not in offered:
            conn.execute(sa.text(
                "INSERT INTO course_offerings (programme, level, semester, course_code, source, hidden) "
                "VALUES (:programme, :level, :semester, :code, 'timetable', :hidden)"
            ), {"programme": programme, "level": level, "semester": semester, "code": code, "hidden": False})


def downgrade() -> None:
    codes = tuple(c[0] for c in NEW_COURSES)
    conn = op.get_bind()
    for code in codes:
        conn.execute(sa.text("DELETE FROM course_offerings WHERE course_code = :c AND source = 'timetable'"), {"c": code})
        conn.execute(sa.text("DELETE FROM courses WHERE code = :c AND source = 'timetable'"), {"c": code})
