"""Password strength rules and hostile input (SQL injection, oversized fields)."""
import pytest
import sqlalchemy as sa

from app.database import engine
from app.services.password_policy import password_problems
from tests.conftest import add_result, login, register


@pytest.mark.parametrize("password", ["Short1!A", "Correct-Horse-1", "Kofi's Pass 2026"])
def test_strong_password_accepted(password):
    assert password_problems(password) == []


@pytest.mark.parametrize("password,missing", [
    ("Ab1!", "at least 8 characters"),
    ("alllowercase1!", "an uppercase letter"),
    ("ALLUPPERCASE1!", "a lowercase letter"),
    ("NoNumbersHere!", "a number"),
    ("NoSymbols123", "a symbol such as ! @ # or ?"),
    ("Password123", "a symbol such as ! @ # or ?"),
])
def test_weak_passwords_rejected(password, missing):
    assert missing in password_problems(password)


def test_common_and_personal_passwords_rejected():
    assert "not a common or easily guessed password" in password_problems("P@ssw0rd")
    assert "not your name or email address" in password_problems("Mensah@2026", email="ama@gmail.com", name="Ama Mensah")
    assert "not your name or email address" in password_problems("Kwabena#99", email="kwabena.o@gmail.com")


def test_register_rejects_weak_password_with_reason(client):
    res = register(client, password="password123")
    assert res.status_code == 400
    assert "uppercase" in res.json()["detail"] and "symbol" in res.json()["detail"]


def test_reset_rejects_weak_and_reused_password(client, no_real_email):
    register(client)
    client.post("/auth/forgot-password", json={"email": "ama@gmail.com"})
    token = no_real_email[0]["reset_token"]
    weak = client.post("/auth/reset-password", json={"token": token, "new_password": "weakpass"})
    assert weak.status_code == 400 and "uppercase" in weak.json()["detail"]
    reused = client.post("/auth/reset-password", json={"token": token, "new_password": "Correct-Horse-1"})
    assert reused.status_code == 400 and "not used" in reused.json()["detail"]


INJECTIONS = [
    "' OR '1'='1",
    "' OR 1=1 --",
    "admin'--",
    "1; DROP TABLE students; --",
    "\'; DELETE FROM results; --",
    "' UNION SELECT password_hash FROM students --",
]


@pytest.mark.parametrize("payload", INJECTIONS)
def test_login_is_not_injectable(client, payload):
    register(client)
    res = client.post("/auth/login", data={"username": payload, "password": payload})
    assert res.status_code == 401
    res = client.post("/auth/login", data={"username": "ama@gmail.com", "password": payload})
    assert res.status_code == 401


def test_injection_strings_are_stored_as_plain_text(client):
    register(client)
    headers = login(client)
    payload = "'); DROP TABLE results; --"
    res = client.post("/results/", headers=headers, json={
        "course_code": "ABC101", "course_name": payload, "credit_hours": 3,
        "grade": "A", "academic_year": "2025/2026", "semester": 1,
    })
    assert res.status_code == 201, res.text
    assert res.json()["course_name"] == payload
    # Tables are all still there and the row reads back unchanged
    with engine.connect() as conn:
        assert "results" in sa.inspect(conn).get_table_names()
        assert "students" in sa.inspect(conn).get_table_names()
    rows = client.get("/results/me", headers=headers).json()["results"]
    assert rows[0]["course_name"] == payload


def test_injection_in_query_parameters(client):
    register(client)
    headers = login(client)
    assert client.get("/results/me", headers=headers, params={"enrollment_id": "1 OR 1=1"}).status_code == 422
    add_result(client, headers, "A1", "A")
    normal = client.get("/gpa/semester", headers=headers, params={"academic_year": "2025/2026", "semester": 1})
    assert normal.json()["semester_gpa"] == 4.0
    hostile = client.get("/gpa/semester", headers=headers,
                         params={"academic_year": "2025/2026' OR '1'='1", "semester": 1})
    assert hostile.json()["semester_gpa"] == 0.0  # treated as a literal (non-matching) year


def test_oversized_input_rejected(client):
    res = register(client, name="A" * 5000)
    assert res.status_code == 422
