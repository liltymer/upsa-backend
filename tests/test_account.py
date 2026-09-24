"""Changing the password and deleting the account from the profile page."""
from tests.conftest import PASSWORD, add_result, login

NEW = "Sankofa#Grade-2026"


def test_change_password(client, student_headers):
    res = client.post("/students/me/password", headers=student_headers,
                      json={"current_password": PASSWORD, "new_password": NEW})
    assert res.status_code == 200, res.text
    assert client.post("/auth/login", data={"username": "ama@gmail.com", "password": PASSWORD}).status_code == 401
    login(client, password=NEW)


def test_change_password_checks(client, student_headers):
    wrong = client.post("/students/me/password", headers=student_headers,
                        json={"current_password": "not-it", "new_password": NEW})
    assert wrong.status_code == 400 and "current password" in wrong.json()["detail"]
    weak = client.post("/students/me/password", headers=student_headers,
                       json={"current_password": PASSWORD, "new_password": "password"})
    assert weak.status_code == 400
    same = client.post("/students/me/password", headers=student_headers,
                       json={"current_password": PASSWORD, "new_password": PASSWORD})
    assert same.status_code == 400 and "different" in same.json()["detail"]
    assert client.post("/students/me/password", json={"current_password": PASSWORD, "new_password": NEW}).status_code == 401


def test_delete_account(client, student_headers):
    add_result(client, student_headers, "DIPC001", "A")
    client.post("/auth/forgot-password", json={"email": "ama@gmail.com"})
    wrong = client.request("DELETE", "/students/me", headers=student_headers, json={"password": "nope", "confirm": "DELETE"})
    assert wrong.status_code == 400
    missing = client.request("DELETE", "/students/me", headers=student_headers, json={"password": PASSWORD, "confirm": "delete"})
    assert missing.status_code == 422

    res = client.request("DELETE", "/students/me", headers=student_headers, json={"password": PASSWORD, "confirm": "DELETE"})
    assert res.status_code == 200, res.text
    assert client.post("/auth/login", data={"username": "ama@gmail.com", "password": PASSWORD}).status_code == 401
    assert client.get("/students/me", headers=student_headers).status_code == 401


def test_admin_cannot_self_delete(client, admin_headers):
    res = client.request("DELETE", "/students/me", headers=admin_headers, json={"password": PASSWORD, "confirm": "DELETE"})
    assert res.status_code == 400
