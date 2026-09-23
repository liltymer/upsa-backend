"""Baseline — the schema the app created with Base.metadata.create_all() before migrations existed.

Each table is only created if missing, so this runs cleanly both on a fresh
database and on the existing production database (where it is a no-op).

Revision ID: 0001_baseline
Revises:
Create Date: 2026-09-23
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001_baseline"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _existing_tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    existing = _existing_tables()

    if "students" not in existing:
        op.create_table(
            "students",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("index_number", sa.String(), nullable=False),
            sa.Column("email", sa.String(), nullable=False),
            sa.Column("password_hash", sa.String(), nullable=False),
            sa.Column("programme", sa.String(), nullable=False),
            sa.Column("level", sa.Integer(), nullable=False),
            sa.Column("academic_year", sa.String(), nullable=False),
            sa.Column("role", sa.String(), nullable=True),
        )
        op.create_index("ix_students_id", "students", ["id"])
        op.create_index("ix_students_index_number", "students", ["index_number"], unique=True)
        op.create_index("ix_students_email", "students", ["email"], unique=True)

    if "results" not in existing:
        op.create_table(
            "results",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False),
            sa.Column("course_code", sa.String(), nullable=False),
            sa.Column("course_name", sa.String(), nullable=False),
            sa.Column("credit_hours", sa.Integer(), nullable=False),
            sa.Column("year", sa.Integer(), nullable=False),
            sa.Column("semester", sa.Integer(), nullable=False),
            sa.Column("grade", sa.String(), nullable=False),
            sa.Column("grade_point", sa.Float(), nullable=False),
        )
        op.create_index("ix_results_id", "results", ["id"])

    if "courses" not in existing:
        op.create_table(
            "courses",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("code", sa.String(), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("credit_hours", sa.Integer(), nullable=False),
            sa.Column("programme", sa.String(), nullable=True),
            sa.Column("level", sa.Integer(), nullable=True),
        )
        op.create_index("ix_courses_id", "courses", ["id"])
        op.create_index("ix_courses_code", "courses", ["code"], unique=True)

    if "announcements" not in existing:
        op.create_table(
            "announcements",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("title", sa.String(200), nullable=False),
            sa.Column("message", sa.Text(), nullable=False),
            sa.Column("priority", sa.String(20), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_announcements_id", "announcements", ["id"])

    if "password_reset_tokens" not in existing:
        op.create_table(
            "password_reset_tokens",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id"), nullable=False),
            sa.Column("token", sa.String(64), nullable=False),
            sa.Column("is_used", sa.Boolean(), nullable=True),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_password_reset_tokens_id", "password_reset_tokens", ["id"])
        op.create_index("ix_password_reset_tokens_token", "password_reset_tokens", ["token"], unique=True)


def downgrade() -> None:
    for table in ["password_reset_tokens", "announcements", "courses", "results", "students"]:
        op.drop_table(table)
