from tests.conftest import login, register


def test_register_and_login_case_insensitive_email(client):
    assert register(client, email="Ama@Gmail.com").status_code == 201
    headers = login(client, email="AMA@gmail.com")
    assert client.get("/students/me", headers=headers).json()["email"] == "ama@gmail.com"


def test_register_rejects_short_password(client):
    assert register(client, password="short").status_code == 422


def test_register_rejects_duplicate(client):
    assert register(client).status_code == 201
    assert register(client).status_code == 409


def test_register_rejects_bad_academic_year(client):
    res = client.post("/auth/register", json={
        "name": "Kofi", "index_number": "1", "email": "k@gmail.com",
        "password": "long-enough-1", "programme": "BSc IT",
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
    res = client.post("/auth/reset-password", json={"token": raw, "new_password": "brand-new-pass"})
    assert res.status_code == 200
    assert client.post("/auth/login", data={"username": "ama@gmail.com", "password": "brand-new-pass"}).status_code == 200
    # single use
    assert client.post("/auth/reset-password", json={"token": raw, "new_password": "again-new-pass"}).status_code == 400
