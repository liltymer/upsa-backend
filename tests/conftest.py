import os
import tempfile

# Configure the app for tests before anything under app/ is imported.
# load_dotenv() does not override variables that are already set.
_db_dir = tempfile.mkdtemp(prefix="gradeiq-tests-")
os.environ["DATABASE_URL"] = f"sqlite:///{_db_dir}/test.db"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["ENVIRONMENT"] = "production"
os.environ["ALLOWED_ORIGINS"] = "https://gradeiq-upsa.vercel.app"

import pytest  # noqa: E402
import sqlalchemy as sa  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.migrate import run_migrations  # noqa: E402
from app.models.student import Student  # noqa: E402
from app.services.rate_limit import reset_rate_limits  # noqa: E402

PASSWORD = "correct-horse-1"


def reset_database():
    """Empty database, then the real migrations — so tests exercise them too."""
    with engine.begin() as conn:
        conn.exec_driver_sql("PRAGMA foreign_keys=OFF")
        for table in sa.inspect(conn).get_table_names():
            conn.exec_driver_sql(f'DROP TABLE IF EXISTS "{table}"')
    run_migrations()


@pytest.fixture(autouse=True)
def no_real_email(monkeypatch):
    sent = []
    monkeypatch.setattr(
        "app.routes.password_reset.send_reset_email",
        lambda **kwargs: sent.append(kwargs),
    )
    return sent


@pytest.fixture(autouse=True)
def fresh_db():
    reset_database()
    reset_rate_limits()
    yield


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def register(client, email="ama@gmail.com", index_number="10212345", password=PASSWORD, **overrides):
    body = {
        "name": "Ama Mensah",
        "index_number": index_number,
        "email": email,
        "password": password,
        "programme": "Diploma in Information Technology Management",
        "level": 100,
        "academic_year": "2025/2026",
    }
    body.update(overrides)
    return client.post("/auth/register", json=body)


def login(client, email="ama@gmail.com", password=PASSWORD):
    res = client.post("/auth/login", data={"username": email, "password": password})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def add_result(client, headers, code, grade, credits=3, academic_year="2025/2026", semester=1, **extra):
    res = client.post("/results/", headers=headers, json={
        "course_code": code, "course_name": code, "credit_hours": credits,
        "grade": grade, "academic_year": academic_year, "semester": semester, **extra,
    })
    assert res.status_code == 201, res.text
    return res.json()


@pytest.fixture
def student_headers(client):
    assert register(client).status_code == 201
    return login(client)


@pytest.fixture
def admin_headers(client, db):
    assert register(client, email="admin@gmail.com", index_number="ADMIN1").status_code == 201
    admin = db.query(Student).filter(Student.email == "admin@gmail.com").one()
    admin.role = "admin"
    db.commit()
    return login(client, email="admin@gmail.com")
