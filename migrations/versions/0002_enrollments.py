"""Programme enrollments — support diploma → degree top-up students.

Moves index number / programme / level off `students` onto a new `enrollments`
table, links every result to an enrollment, and replaces the relative
`results.year` (1–4) with the UPSA-style academic year ("2024/2025").

Existing data:
* Every student gets one current enrollment built from their profile.
* A student on a degree programme who also has DIP-coded (diploma) results
  had topped up in place — their diploma results were being averaged into the
  degree CGPA. Those results are split into a completed diploma enrollment
  flagged `needs_review` so the student can add the old index number.
* Each result's academic year is derived from the enrollment's start year.
  Students can correct any of this from the app.

Revision ID: 0002_enrollments
Revises: 0001_baseline
Create Date: 2026-09-23
"""
import re
from datetime import date
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002_enrollments"
down_revision: Union[str, Sequence[str], None] = "0001_baseline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PREVIOUS_DIPLOMA_PLACEHOLDER = "Diploma (previous programme)"


# Helpers are copied here on purpose: a migration must keep working even if app code changes.
def _start_year(academic_year) -> int:
    match = re.match(r"^\s*(\d{4})\s*/\s*(\d{4})\s*$", academic_year or "")
    if match:
        return int(match.group(1))
    today = date.today()
    return today.year if today.month >= 8 else today.year - 1


def _ay(start: int) -> str:
    return f"{start}/{start + 1}"


def _level(value) -> int:
    try:
        level = int(value)
    except (TypeError, ValueError):
        return 100
    return min(max(round(level / 100) * 100, 100), 400)


def _is_diploma_programme(programme) -> bool:
    return (programme or "").strip().lower().startswith("diploma")


def _is_diploma_code(code) -> bool:
    return (code or "").strip().upper().startswith("DIP")


def upgrade() -> None:
    bind = op.get_bind()

    op.create_table(
        "enrollments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False),
        sa.Column("index_number", sa.String(30), nullable=True),
        sa.Column("programme", sa.String(200), nullable=False),
        sa.Column("award_type", sa.String(20), nullable=False),
        sa.Column("entry_level", sa.Integer(), nullable=False),
        sa.Column("current_level", sa.Integer(), nullable=False),
        sa.Column("start_academic_year", sa.String(9), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("needs_review", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_enrollments_id", "enrollments", ["id"])
    op.create_index("ix_enrollments_student_id", "enrollments", ["student_id"])
    op.create_index("ix_enrollments_index_number", "enrollments", ["index_number"], unique=True)

    with op.batch_alter_table("results") as batch:
        batch.add_column(sa.Column("enrollment_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("academic_year", sa.String(9), nullable=True))

    enrollments = sa.table(
        "enrollments",
        sa.column("id", sa.Integer), sa.column("student_id", sa.Integer),
        sa.column("index_number", sa.String), sa.column("programme", sa.String),
        sa.column("award_type", sa.String), sa.column("entry_level", sa.Integer),
        sa.column("current_level", sa.Integer), sa.column("start_academic_year", sa.String),
        sa.column("status", sa.String), sa.column("is_current", sa.Boolean),
        sa.column("needs_review", sa.Boolean),
    )

    def add_enrollment(**values) -> int:
        result = bind.execute(enrollments.insert().values(**values).returning(enrollments.c.id))
        return result.scalar_one()

    students = bind.execute(sa.text(
        "SELECT id, index_number, programme, level, academic_year FROM students ORDER BY id"
    )).mappings().all()

    for s in students:
        results = bind.execute(
            sa.text("SELECT id, course_code, year FROM results WHERE student_id = :sid"),
            {"sid": s["id"]},
        ).mappings().all()

        profile_start = _start_year(s["academic_year"])
        level = _level(s["level"])
        programme = (s["programme"] or "Other").strip() or "Other"
        on_diploma = _is_diploma_programme(programme)
        has_diploma_results = any(_is_diploma_code(r["course_code"]) for r in results)

        assignments: list[tuple[int, int, str]] = []  # (result_id, enrollment_id, academic_year)

        if not on_diploma and has_diploma_results:
            # Topped up in place: separate the diploma from the degree.
            current_level = max(level, 300)
            degree_start = profile_start - (current_level - 300) // 100
            diploma_start = degree_start - 2

            degree_id = add_enrollment(
                student_id=s["id"], index_number=s["index_number"], programme=programme,
                award_type="degree", entry_level=300, current_level=current_level,
                start_academic_year=_ay(degree_start), status="active",
                is_current=True, needs_review=True,
            )
            diploma_id = add_enrollment(
                student_id=s["id"], index_number=None, programme=PREVIOUS_DIPLOMA_PLACEHOLDER,
                award_type="diploma", entry_level=100, current_level=200,
                start_academic_year=_ay(diploma_start), status="completed",
                is_current=False, needs_review=True,
            )
            for r in results:
                year = max(int(r["year"] or 1), 1)
                if _is_diploma_code(r["course_code"]):
                    assignments.append((r["id"], diploma_id, _ay(diploma_start + min(year, 2) - 1)))
                else:
                    offset = year - 3 if year >= 3 else year - 1
                    assignments.append((r["id"], degree_id, _ay(degree_start + offset)))
        else:
            start = profile_start - (level - 100) // 100
            enrollment_id = add_enrollment(
                student_id=s["id"], index_number=s["index_number"], programme=programme,
                award_type="diploma" if on_diploma else "degree", entry_level=100,
                current_level=level, start_academic_year=_ay(start), status="active",
                is_current=True, needs_review=False,
            )
            for r in results:
                year = max(int(r["year"] or 1), 1)
                assignments.append((r["id"], enrollment_id, _ay(start + year - 1)))

        for result_id, enrollment_id, academic_year in assignments:
            bind.execute(
                sa.text("UPDATE results SET enrollment_id = :e, academic_year = :ay WHERE id = :id"),
                {"e": enrollment_id, "ay": academic_year, "id": result_id},
            )

    # Orphaned results (student row missing) cannot be attributed — drop them.
    bind.execute(sa.text("DELETE FROM results WHERE enrollment_id IS NULL"))

    with op.batch_alter_table("results") as batch:
        batch.alter_column("enrollment_id", existing_type=sa.Integer(), nullable=False)
        batch.alter_column("academic_year", existing_type=sa.String(9), nullable=False)
        batch.create_foreign_key(
            "fk_results_enrollment_id", "enrollments", ["enrollment_id"], ["id"], ondelete="CASCADE",
        )
        batch.create_index("ix_results_enrollment_id", ["enrollment_id"])
        batch.create_index("ix_results_student_id", ["student_id"])
        batch.drop_column("year")

    # Academic details now live on enrollments.
    student_indexes = {ix["name"] for ix in sa.inspect(bind).get_indexes("students")}
    if "ix_students_index_number" in student_indexes:
        op.drop_index("ix_students_index_number", table_name="students")

    bind.execute(sa.text("UPDATE students SET role = 'student' WHERE role IS NULL"))
    with op.batch_alter_table("students") as batch:
        batch.alter_column("role", existing_type=sa.String(), nullable=False, server_default="student")
        batch.drop_column("index_number")
        batch.drop_column("programme")
        batch.drop_column("level")
        batch.drop_column("academic_year")

    # Reset tokens are now stored hashed; outstanding raw tokens (max 1 hour old) are invalidated.
    bind.execute(sa.text("DELETE FROM password_reset_tokens"))


def downgrade() -> None:
    bind = op.get_bind()

    with op.batch_alter_table("students") as batch:
        batch.add_column(sa.Column("index_number", sa.String(), nullable=True))
        batch.add_column(sa.Column("programme", sa.String(), nullable=True))
        batch.add_column(sa.Column("level", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("academic_year", sa.String(), nullable=True))

    with op.batch_alter_table("results") as batch:
        batch.add_column(sa.Column("year", sa.Integer(), nullable=True))

    rows = bind.execute(sa.text(
        "SELECT id, student_id, index_number, programme, current_level, start_academic_year, is_current "
        "FROM enrollments ORDER BY is_current DESC, id"
    )).mappings().all()

    seen: set[int] = set()
    for e in rows:
        start = _start_year(e["start_academic_year"])
        for r in bind.execute(
            sa.text("SELECT id, academic_year FROM results WHERE enrollment_id = :eid"), {"eid": e["id"]}
        ).mappings():
            bind.execute(
                sa.text("UPDATE results SET year = :y WHERE id = :id"),
                {"y": max(_start_year(r["academic_year"]) - start + 1, 1), "id": r["id"]},
            )
        if e["student_id"] in seen:
            continue
        seen.add(e["student_id"])
        current_start = start + (int(e["current_level"]) - 100) // 100
        bind.execute(
            sa.text(
                "UPDATE students SET index_number = :idx, programme = :prog, level = :lvl, "
                "academic_year = :ay WHERE id = :sid"
            ),
            {
                "idx": e["index_number"] or f"UNKNOWN-{e['student_id']}",
                "prog": e["programme"], "lvl": e["current_level"],
                "ay": _ay(current_start), "sid": e["student_id"],
            },
        )

    bind.execute(sa.text("UPDATE results SET year = 1 WHERE year IS NULL"))

    with op.batch_alter_table("results") as batch:
        batch.drop_index("ix_results_enrollment_id")
        batch.drop_index("ix_results_student_id")
        batch.drop_constraint("fk_results_enrollment_id", type_="foreignkey")
        batch.drop_column("enrollment_id")
        batch.drop_column("academic_year")
        batch.alter_column("year", existing_type=sa.Integer(), nullable=False)

    op.drop_table("enrollments")
    op.create_index("ix_students_index_number", "students", ["index_number"], unique=True)
