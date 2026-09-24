from app.models.password_reset import PasswordResetToken
from app.models.student import Student
from tests.conftest import register


def test_dev_routes_not_mounted_in_production(client, admin_headers):
    assert client.post("/dev/seed", headers=admin_headers).status_code == 404
    assert client.delete("/dev/reset", headers=admin_headers).status_code == 404


def test_course_creation_requires_admin(client, student_headers, admin_headers):
    course = {"code": "zzz101", "name": "New Elective", "credit_hours": 3}

    assert client.post("/courses/", json=course).status_code == 401
    assert client.post("/courses/", json=course, headers=student_headers).status_code == 403

    res = client.post("/courses/", json=course, headers=admin_headers)
    assert res.status_code == 201
    assert res.json()["code"] == "ZZZ101"

    assert client.post("/courses/", json=course, headers=admin_headers).status_code == 409


def test_admin_course_duplicate_returns_conflict(client, admin_headers):
    course = {"code": "ZZZ102", "name": "New Elective", "credit_hours": 3}
    assert client.post("/admin/courses", json=course, headers=admin_headers).status_code == 201
    assert client.post("/admin/courses", json=course, headers=admin_headers).status_code == 409


def test_unauthenticated_student_create_endpoint_removed(client):
    res = client.post("/students/", params={"name": "x", "index_number": "y"})
    assert res.status_code in (404, 405)


def test_admin_routes_forbidden_for_students(client, student_headers):
    assert client.get("/admin/users", headers=student_headers).status_code == 403


def test_cors_only_allows_configured_origin(client):
    allowed = client.get("/", headers={"Origin": "https://gradeiq-upsa.vercel.app"})
    assert allowed.headers.get("access-control-allow-origin") == "https://gradeiq-upsa.vercel.app"

    blocked = client.get("/", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in blocked.headers


def test_admin_can_delete_student_with_reset_token(client, db, admin_headers):
    assert register(client).status_code == 201
    student_id = db.query(Student.id).filter(Student.email == "ama@gmail.com").scalar()
    client.post("/auth/forgot-password", json={"email": "ama@gmail.com"})
    assert db.query(PasswordResetToken).filter_by(student_id=student_id).count() == 1

    res = client.delete(f"/admin/users/{student_id}", headers=admin_headers)
    assert res.status_code == 200, res.text
    assert db.query(Student).filter_by(id=student_id).first() is None


def test_security_headers(client):
    res = client.get("/")
    assert res.headers["x-content-type-options"] == "nosniff"
    assert res.headers["x-frame-options"] == "DENY"
    assert "strict-transport-security" in res.headers
