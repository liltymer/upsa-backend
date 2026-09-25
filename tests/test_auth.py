from tests.conftest import PASSWORD, login, register


def test_register_and_login_case_insensitive_email(client):
    assert register(client, email="Ama@Gmail.com").status_code == 201
    headers = login(client, email="AMA@gmail.com")
    assert client.get("/students/me", headers=headers).json()["email"] == "ama@gmail.com"


def test_register_rejects_short_password(client):
    res = register(client, password="Sh0rt!")
    assert res.status_code == 400
    assert "at least 8 characters" in res.json()["detail"]


def test_register_rejects_duplicate(client):
    assert register(client).status_code == 201
    assert register(client).status_code == 409


def test_register_rejects_bad_academic_year(client):
    res = client.post("/auth/register", json={
        "name": "Kofi", "index_number": "1", "email": "k@gmail.com",
        "password": "Long-Enough-1", "programme": "BSc IT",
        "level": 100, "academic_year": "2025/26/x",
    })
    assert res.status_code == 400


def test_login_wrong_password(client):
    register(client)
    res = client.post("/auth/login", data={"username": "ama@gmail.com", "password": "nope-nope"})
    assert res.status_code == 401


def test_login_is_rate_limited(client):
    register(client)
    codes = [
        client.post("/auth/login", data={"username": "ama@gmail.com", "password": "wrong-pass"}).status_code
        for _ in range(11)
    ]
    assert codes[:10] == [401] * 10
    assert codes[10] == 429


def test_reset_token_is_stored_hashed(client, db, no_real_email):
    from app.models.password_reset import PasswordResetToken
    register(client)
    client.post("/auth/forgot-password", json={"email": "AMA@gmail.com"})
    raw = no_real_email[0]["reset_token"]
    stored = db.query(PasswordResetToken).one().token
    assert stored != raw and len(stored) == 64

    assert client.get(f"/auth/verify-reset-token/{raw}").status_code == 200
    res = client.post("/auth/reset-password", json={"token": raw, "new_password": "Brand-New-Pass-2"})
    assert res.status_code == 200
    assert client.post("/auth/login", data={"username": "ama@gmail.com", "password": "Brand-New-Pass-2"}).status_code == 200
    # single use
    assert client.post("/auth/reset-password", json={"token": raw, "new_password": "Again-New-Pass-3"}).status_code == 400


def test_login_returns_user_summary(client, student_headers):
    res = client.post("/auth/login", data={"username": "10212345", "password": PASSWORD})
    assert res.status_code == 200
    user = res.json()["user"]
    assert user["name"] == "Ama Mensah" and user["role"] == "student" and user["index_number"] == "10212345"


def test_old_password_hashes_upgrade_on_login(client, db, student_headers):
    from passlib.context import CryptContext

    from app.models.student import Student
    from app.services.auth import BCRYPT_ROUNDS
    student = db.query(Student).filter(Student.email == "ama@gmail.com").one()
    student.password_hash = CryptContext(schemes=["bcrypt"], bcrypt__rounds=12).hash(PASSWORD)
    db.commit()
    assert client.post("/auth/login", data={"username": "ama@gmail.com", "password": PASSWORD}).status_code == 200
    db.refresh(student)
    assert student.password_hash.startswith(f"$2b${BCRYPT_ROUNDS}$")
    # Still works after the upgrade
    assert client.post("/auth/login", data={"username": "ama@gmail.com", "password": PASSWORD}).status_code == 200
