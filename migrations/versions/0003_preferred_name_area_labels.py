"""Preferred name for greetings and custom subject-area names per programme.

Revision ID: 0003_names
Revises: 0002_enrollments
Create Date: 2026-09-23
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003_names"
down_revision: Union[str, Sequence[str], None] = "0002_enrollments"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("students") as batch:
        batch.add_column(sa.Column("preferred_name", sa.String(60), nullable=True))
    with op.batch_alter_table("enrollments") as batch:
        batch.add_column(sa.Column("area_labels", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("enrollments") as batch:
        batch.drop_column("area_labels")
    with op.batch_alter_table("students") as batch:
        batch.drop_column("preferred_name")
