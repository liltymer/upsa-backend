"""Upgrading a database in the pre-enrollment shape that production has today."""
import sqlalchemy as sa

from app.database import engine
from app.migrate import alembic_config, run_migrations
from alembic import command
from tests.conftest import login

def _legacy_db():
    """Empty database migrated only to the baseline (the old schema), with realistic rows."""
    from app.services.auth import hash_password

    with engine.begin() as conn:
        conn.exec_driver_sql("PRAGMA foreign_keys=OFF")
        for table in sa.inspect(conn).get_table_names():
            conn.exec_driver_sql(f'DROP TABLE IF EXISTS "{table}"')
    run_migrations("0001_baseline")

    pw = hash_password("correct-horse-1")
    with engine.begin() as conn:
        conn.execute(sa.text(
            "INSERT INTO students (id, name, index_number, email, password_hash, programme, level, academic_year, role) VALUES "
            "(1, 'Diploma Dee', '10324631', 'dee@gmail.com', :pw, 'Diploma in Information Technology Management', 200, '2025/2026', 'student'),"
            "(2, 'Topped Tom', '20260001', 'tom@gmail.com', :pw, 'Bachelor of Science in Information Technology', 300, '2026/2027', NULL)"
        ), {"pw": pw})
        conn.execute(sa.text(
            "INSERT INTO results (student_id, course_code, course_name, credit_hours, year, semester, grade, grade_point) VALUES "
            # Dee: plain diploma student, Year 1 and Year 2
            "(1, 'DIPT001', 'Computer Applications', 3, 1, 1, 'A', 4.0),"
            "(1, 'DIPT050', 'Project Work', 4, 2, 2, 'B', 3.0),"
            # Tom: switched his profile to the degree and kept adding results under one CGPA
            "(2, 'DIPT001', 'Computer Applications', 3, 1, 1, 'A', 4.0),"
            "(2, 'DIPC003', 'Business Management', 3, 2, 1, 'C', 1.5),"
            "(2, 'BIT301', 'Systems Analysis', 3, 3, 1, 'B', 3.0)"
        ))
        conn.execute(sa.text(
            "INSERT INTO password_reset_tokens (student_id, token, is_used, expires_at) "
            "VALUES (1, 'raw-token', 0, '2099-01-01')"
        ))


def test_upgrade_moves_profiles_into_enrollments(client):
    _legacy_db()
    run_migrations()

    with engine.connect() as conn:
        enrollments = conn.execute(sa.text(
            "SELECT student_id, index_number, programme, award_type, entry_level, current_level, "
            "start_academic_year, status, is_current, needs_review FROM enrollments ORDER BY student_id, id"
        )).mappings().all()
        results = conn.execute(sa.text(
            "SELECT r.student_id, r.course_code, r.academic_year, e.award_type "
            "FROM results r JOIN enrollments e ON e.id = r.enrollment_id ORDER BY r.id"
        )).all()
        assert conn.execute(sa.text("SELECT COUNT(*) FROM password_reset_tokens")).scalar() == 0

    dee, tom_degree, tom_diploma = enrollments
    assert dict(dee) == {
        "student_id": 1, "index_number": "10324631", "programme": "Diploma in Information Technology Management",
        "award_type": "diploma", "entry_level": 100, "current_level": 200, "start_academic_year": "2024/2025",
        "status": "active", "is_current": True, "needs_review": False,
    }
    # Tom's diploma results are split out of his degree CGPA
    assert tom_degree["award_type"] == "degree" and tom_degree["entry_level"] == 300
    assert tom_degree["start_academic_year"] == "2026/2027" and tom_degree["is_current"]
    assert tom_diploma["award_type"] == "diploma" and tom_diploma["status"] == "completed"
    assert tom_diploma["index_number"] is None and tom_diploma["needs_review"]

    assert results == [
        (1, "DIPT001", "2024/2025", "diploma"),
        (1, "DIPT050", "2025/2026", "diploma"),
        (2, "DIPT001", "2024/2025", "diploma"),
        (2, "DIPC003", "2025/2026", "diploma"),
        (2, "BIT301", "2026/2027", "degree"),
    ]

    # Existing credentials keep working, and the degree CGPA no longer includes the diploma
    headers = login(client, email="tom@gmail.com")
    assert client.get("/gpa/cgpa", headers=headers).json()["cgpa"] == 3.0
    dash = client.get("/dashboard/me", headers=headers).json()
    assert dash["needs_review"] is True
    assert dash["other_programmes"][0]["cgpa"] == 2.75


def test_downgrade_restores_legacy_schema():
    _legacy_db()
    run_migrations()

    config = alembic_config()
    with engine.begin() as conn:
        config.attributes["connection"] = conn
        command.downgrade(config, "0001_baseline")

    with engine.connect() as conn:
        student = conn.execute(sa.text(
            "SELECT index_number, programme, level FROM students WHERE id = 1"
        )).one()
        years = conn.execute(sa.text("SELECT year FROM results WHERE student_id = 1 ORDER BY id")).scalars().all()
    assert tuple(student) == ("10324631", "Diploma in Information Technology Management", 200)
    assert years == [1, 2]
