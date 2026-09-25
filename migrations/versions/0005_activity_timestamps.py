"""When accounts are created and last sign in, and when results are entered.

Revision ID: 0005_activity
Revises: 0004_offerings
Create Date: 2026-09-25
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0005_activity"
down_revision: Union[str, Sequence[str], None] = "0004_offerings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Added without a default first, so existing rows are not all stamped "today"
    with op.batch_alter_table("students") as batch:
        batch.add_column(sa.Column("created_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True))
    with op.batch_alter_table("results") as batch:
        batch.add_column(sa.Column("created_at", sa.DateTime(timezone=True), nullable=True))

    # Existing accounts: the date of their first programme is the best record of sign-up
    op.execute(
        "UPDATE students SET created_at = "
        "(SELECT MIN(e.created_at) FROM enrollments e WHERE e.student_id = students.id)"
    )

    with op.batch_alter_table("students") as batch:
        batch.alter_column("created_at", server_default=sa.func.now())
    with op.batch_alter_table("results") as batch:
        batch.alter_column("created_at", server_default=sa.func.now())


def downgrade() -> None:
    with op.batch_alter_table("results") as batch:
        batch.drop_column("created_at")
    with op.batch_alter_table("students") as batch:
        batch.drop_column("last_login_at")
        batch.drop_column("created_at")
