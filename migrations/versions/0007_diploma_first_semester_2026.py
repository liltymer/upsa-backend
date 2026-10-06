"""Diploma first-year, first-semester course lists from UPSA's 2026/2027 teaching timetable.

The official timetable shows exactly which courses each diploma takes in Level 100,
First Semester. Missing ones are added; courses the system had guessed (loaded from
other timetables) are hidden, not deleted, so students can still type them.

Revision ID: 0007_diploma_l100
Revises: 0006_timetables_oct
Create Date: 2026-10-06
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0007_diploma_l100"
down_revision: Union[str, Sequence[str], None] = "0006_timetables_oct"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

COURSE_LISTS = {
    "Diploma in Management": [
        "DIPC001",
        "DIPC003",
        "DIPC005",
        "DIPC007",
        "DIPC009",
        "DIPC011"
    ],
    "Diploma in Information Technology Management": [
        "DIPC003",
        "DIPC005",
        "DIPC009",
        "DIPT001",
        "DIPT003"
    ],
    "Diploma in Marketing": [
        "DIPC001",
        "DIPC003",
        "DIPC005",
        "DIPC007",
        "DIPC009",
        "DIPC011"
    ],
    "Diploma in Accounting": [
        "DIPC001",
        "DIPC003",
        "DIPC005",
        "DIPC007",
        "DIPC009",
        "DIPC011"
    ],
    "Diploma in Public Relations": [
        "DIPC001",
        "DIPC007",
        "DIPC009",
        "DIPC011",
        "DIPR001",
        "DIPR003"
    ]
}


def upgrade() -> None:
    conn = op.get_bind()
    if not conn.execute(sa.text("SELECT 1 FROM courses WHERE code = 'DIPC009'")).first():
        conn.execute(sa.text(
            "INSERT INTO courses (code, name, credit_hours, level, semester, source) "
            "VALUES ('DIPC009', 'Introduction to Information Technology', 3, 100, 1, 'timetable')"
        ))
    for programme, codes in COURSE_LISTS.items():
        rows = conn.execute(sa.text(
            "SELECT id, course_code, source, hidden FROM course_offerings "
            "WHERE programme = :p AND level = 100 AND semester = 1"
        ), {"p": programme}).fetchall()
        listed = {r.course_code: r for r in rows}
        for code in codes:
            if code not in listed:
                conn.execute(sa.text(
                    "INSERT INTO course_offerings (programme, level, semester, course_code, source, hidden) "
                    "VALUES (:p, 100, 1, :c, 'timetable', :h)"
                ), {"p": programme, "c": code, "h": False})
            elif listed[code].hidden and listed[code].source == "timetable":
                conn.execute(sa.text("UPDATE course_offerings SET hidden = :h WHERE id = :id"), {"h": False, "id": listed[code].id})
        # Guesses from other timetables that this programme does not take; admin entries are left alone
        for code, row in listed.items():
            if code not in codes and row.source == "timetable" and not row.hidden:
                conn.execute(sa.text("UPDATE course_offerings SET hidden = :h WHERE id = :id"), {"h": True, "id": row.id})


def downgrade() -> None:
    # Course lists are data; nothing to undo structurally
    pass
