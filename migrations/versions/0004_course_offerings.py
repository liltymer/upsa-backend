"""Course semesters, programme course lists, and UPSA courses from the published timetables.

Revision ID: 0004_offerings
Revises: 0003_names
Create Date: 2026-09-24
"""
import json
from pathlib import Path
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0004_offerings"
down_revision: Union[str, Sequence[str], None] = "0003_names"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DATA = Path(__file__).resolve().parents[2] / "app" / "data" / "upsa_courses.json"
# Timetables do not list credit hours; most UPSA courses carry 3, and students can correct it
DEFAULT_CREDITS = 3


def upgrade() -> None:
    with op.batch_alter_table("courses") as batch:
        batch.add_column(sa.Column("semester", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("source", sa.String(20), nullable=True))

    offerings = op.create_table(
        "course_offerings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("programme", sa.String(), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("semester", sa.Integer(), nullable=False),
        sa.Column("course_code", sa.String(), nullable=False),
        sa.Column("source", sa.String(20), nullable=False, server_default="admin"),
        sa.Column("hidden", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.UniqueConstraint("programme", "level", "semester", "course_code", name="uq_offering"),
    )
    op.create_index("ix_course_offerings_id", "course_offerings", ["id"])
    op.create_index("ix_course_offerings_programme", "course_offerings", ["programme"])

    data = json.loads(DATA.read_text(encoding="utf-8"))
    conn = op.get_bind()
    courses = sa.table(
        "courses",
        sa.column("code", sa.String), sa.column("name", sa.String), sa.column("credit_hours", sa.Integer),
        sa.column("level", sa.Integer), sa.column("semester", sa.Integer), sa.column("source", sa.String),
    )
    # Courses an admin already added keep their details
    existing = {row[0] for row in conn.execute(sa.text("SELECT code FROM courses"))}
    op.bulk_insert(courses, [
        {"code": c["code"], "name": c["name"], "credit_hours": DEFAULT_CREDITS,
         "level": c["level"], "semester": c["semester"], "source": "timetable"}
        for c in data["courses"] if c["code"] not in existing
    ])
    op.bulk_insert(offerings, [
        {"programme": o["programme"], "level": o["level"], "semester": o["semester"],
         "course_code": o["code"], "source": "timetable", "hidden": False}
        for o in data["offerings"]
    ])


def downgrade() -> None:
    op.execute("DELETE FROM courses WHERE source = 'timetable'")
    op.drop_index("ix_course_offerings_programme", table_name="course_offerings")
    op.drop_index("ix_course_offerings_id", table_name="course_offerings")
    op.drop_table("course_offerings")
    with op.batch_alter_table("courses") as batch:
        batch.drop_column("source")
        batch.drop_column("semester")
