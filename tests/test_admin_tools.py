"""Admin tools: accounts and roles, honest analytics, and programme course lists."""
from tests.conftest import add_result, login, register

BSC_IT = "Bachelor of Science in Information Technology"


def test_users_list_shows_roles_and_counts_but_never_grades(client, admin_headers, student_headers):
    add_result(client, student_headers, "DIPC001", "A")
    users = {u["email"]: u for u in client.get("/admin/users", headers=admin_headers).json()["students"]}
    assert users["ama@gmail.com"]["results_count"] == 1 and users["ama@gmail.com"]["role"] == "student"
    assert users["admin@gmail.com"]["role"] == "admin"
    assert not any(k in users["ama@gmail.com"] for k in ("cgpa", "grade", "results"))


def test_make_and_remove_admin(client, admin_headers, student_headers):
    users = {u["email"]: u for u in client.get("/admin/users", headers=admin_headers).json()["students"]}
    ama, me = users["ama@gmail.com"]["id"], users["admin@gmail.com"]["id"]
    assert client.get("/admin/stats", headers=student_headers).status_code == 403

    assert client.put(f"/admin/users/{ama}/role", headers=admin_headers, json={"role": "admin"}).status_code == 200
    assert client.get("/admin/stats", headers=login(client)).status_code == 200
    assert client.put(f"/admin/users/{ama}/role", headers=admin_headers, json={"role": "student"}).status_code == 200
    assert client.get("/admin/stats", headers=login(client)).status_code == 403

    own = client.put(f"/admin/users/{me}/role", headers=admin_headers, json={"role": "student"})
    assert own.status_code == 400
    assert client.put(f"/admin/users/{ama}/role", headers=student_headers, json={"role": "admin"}).status_code == 403
    assert client.put(f"/admin/users/{ama}/role", headers=admin_headers, json={"role": "owner"}).status_code == 422


def test_analytics_uses_upsa_standing(client, admin_headers):
    def student(n, grades):
        email = f"s{n}@gmail.com"
        register(client, email=email, index_number=f"1040000{n}")
        headers = login(client, email=email)
        for i, g in enumerate(grades):
            add_result(client, headers, f"DIPC00{i}", g)
    student(1, ["A", "B"])          # clean record
    student(2, ["B", "F"])          # failed course to clear
    student(3, ["F", "F", "D"])     # CGPA below 1.00: probation
    body = client.get("/admin/analytics", headers=admin_headers).json()
    assert body["standing"] == {"probation": 1, "failed_to_clear": 1, "clean": 1, "no_data": 0}
    assert "risk_distribution" not in body


def test_programme_course_lists(client, admin_headers):
    params = {"programme": BSC_IT, "level": 300, "semester": 1}
    body = client.get("/admin/offerings", headers=admin_headers, params=params).json()
    codes = {o["course_code"]: o for o in body["listed"]}
    assert "BSIT301" in codes and codes["BSIT301"]["credits_confirmed"] is False

    # Hide one, add a new course, and see it in the student suggestions
    hid = client.put(f"/admin/offerings/{codes['BCPC207']['id']}", headers=admin_headers, json={"hidden": True})
    assert hid.status_code == 200
    missing = client.post("/admin/offerings", headers=admin_headers, json={**params, "course_code": "BSIT399"})
    assert missing.status_code == 400
    added = client.post("/admin/offerings", headers=admin_headers,
                        json={**params, "course_code": "bsit399", "course_name": "Cloud Computing", "credit_hours": 3})
    assert added.status_code == 201
    assert client.post("/admin/offerings", headers=admin_headers, json={**params, "course_code": "BSIT399"}).status_code == 409

    register(client, email="it@gmail.com", index_number="10400011", programme=BSC_IT, level=300, academic_year="2026/2027")
    student = login(client, email="it@gmail.com")
    suggested = {c["course_code"] for c in client.get("/courses/suggestions", headers=student,
                 params={"academic_year": "2026/2027", "semester": 1}).json()["courses"]}
    assert "BSIT399" in suggested and "BCPC207" not in suggested


def test_courses_students_entered_can_be_added_or_ignored(client, admin_headers):
    register(client, email="it@gmail.com", index_number="10400011", programme=BSC_IT, level=300, academic_year="2026/2027")
    student = login(client, email="it@gmail.com")
    add_result(client, student, "XYZ301", "B", academic_year="2026/2027", course_name="Special Topic")
    params = {"programme": BSC_IT, "level": 300, "semester": 1}
    extra = client.get("/admin/offerings", headers=admin_headers, params=params).json()["from_students"]
    assert extra == [{"course_code": "XYZ301", "name": "Special Topic", "credit_hours": 3, "students": 1}]

    ignored = client.post("/admin/offerings", headers=admin_headers, json={**params, "course_code": "XYZ301", "hidden": True})
    assert ignored.status_code == 201
    body = client.get("/admin/offerings", headers=admin_headers, params=params).json()
    assert body["from_students"] == []
    assert next(o for o in body["listed"] if o["course_code"] == "XYZ301")["hidden"] is True


def test_offerings_need_admin(client, student_headers):
    params = {"programme": BSC_IT, "level": 300, "semester": 1}
    assert client.get("/admin/offerings", headers=student_headers, params=params).status_code == 403
