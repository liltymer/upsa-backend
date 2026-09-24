"""Pre-filled semesters: UPSA course lists, courses learned from students, and saving a semester at once."""
from app.models.course import CourseOffering
from tests.conftest import add_result, login, register

BSC_IT = "Bachelor of Science in Information Technology"
STATS = "Bachelor of Science in Applied Statistics"  # no published course list


def suggest(client, headers, year, semester):
    res = client.get("/courses/suggestions", headers=headers, params={"academic_year": year, "semester": semester})
    assert res.status_code == 200, res.text
    return res.json()


def codes(body):
    return {c["course_code"] for c in body["courses"]}


def student(client, n, programme=STATS, level=100, year="2025/2026"):
    email = f"s{n}@gmail.com"
    assert register(client, email=email, index_number=f"1030000{n}", programme=programme,
                    level=level, academic_year=year).status_code == 201
    return login(client, email=email)


def test_timetable_courses_are_loaded(client):
    catalogue = {c["code"]: c for c in client.get("/courses/").json()}
    assert catalogue["BSIT301"]["name"] == "Programming"
    assert catalogue["BSIT301"]["level"] == 300 and catalogue["BSIT301"]["semester"] == 1
    assert catalogue["DIPT004"]["name"] == "Computer Hardware Systems I"
    assert len(catalogue) > 300


def test_degree_semester_is_prefilled(client):
    headers = student(client, 1, programme=BSC_IT, level=300, year="2026/2027")
    body = suggest(client, headers, "2026/2027", 1)
    assert body["level"] == 300
    assert {"BSIT301", "BSIT303", "BSIT309", "BCPC207"} <= codes(body)
    first = next(c for c in body["courses"] if c["course_code"] == "BSIT301")
    assert first["course_name"] == "Programming" and first["credit_hours"] == 3
    assert first["credits_confirmed"] is False and first["source"] == "list"


def test_diploma_semester_includes_common_courses(client):
    headers = student(client, 1, programme="Diploma in Information Technology Management")
    body = suggest(client, headers, "2025/2026", 1)
    assert {"DIPT001", "DIPC001"} <= codes(body)
    assert not any(c.startswith("BSIT") for c in codes(body))


def test_courses_are_learned_after_two_students(client):
    first = student(client, 1)
    add_result(client, first, "STAT101", "A", course_name="Probability I", credits=2)
    newcomer = student(client, 3)
    assert "STAT101" not in codes(suggest(client, newcomer, "2025/2026", 1))

    second = student(client, 2)
    add_result(client, second, "STAT101", "C", course_name="Probability I", credits=2)
    learned = next(c for c in suggest(client, newcomer, "2025/2026", 1)["courses"] if c["course_code"] == "STAT101")
    assert learned == {
        "course_code": "STAT101", "course_name": "Probability I", "credit_hours": 2,
        "credits_confirmed": True, "source": "students", "recorded_before": False,
    }
    # Nothing about grades or other students is shared
    assert "grade" not in learned


def test_learning_is_per_level_and_semester(client):
    for n in (1, 2):
        add_result(client, student(client, n), "STAT102", "B", semester=2)
    newcomer = student(client, 3)
    assert "STAT102" not in codes(suggest(client, newcomer, "2025/2026", 1))
    assert "STAT102" in codes(suggest(client, newcomer, "2025/2026", 2))


def test_own_courses_are_skipped_or_flagged(client):
    headers = student(client, 1, programme=BSC_IT, level=300, year="2025/2026")
    add_result(client, headers, "BSIT301", "D", academic_year="2025/2026", semester=1)
    this_semester = suggest(client, headers, "2025/2026", 1)
    assert "BSIT301" not in codes(this_semester)
    # Level 400 a year later: a resit of BSIT301 would be flagged, not hidden
    later = suggest(client, headers, "2026/2027", 1)
    assert later["level"] == 400


def test_hidden_offering_is_not_suggested(client, db):
    headers = student(client, 1, programme=BSC_IT, level=300, year="2026/2027")
    offering = db.query(CourseOffering).filter_by(programme=BSC_IT, level=300, semester=1, course_code="BCPC207").one()
    offering.hidden = True
    db.commit()
    assert "BCPC207" not in codes(suggest(client, headers, "2026/2027", 1))


def test_suggestions_need_login_and_a_valid_year(client):
    assert client.get("/courses/suggestions", params={"academic_year": "2025/2026", "semester": 1}).status_code == 401
    headers = student(client, 1)
    res = client.get("/courses/suggestions", headers=headers, params={"academic_year": "2025", "semester": 1})
    assert res.status_code == 400
    res = client.get("/courses/suggestions", headers=headers, params={"academic_year": "2025/2026", "semester": 3})
    assert res.status_code == 422


def semester_body(courses, year="2025/2026", semester=1):
    return {"academic_year": year, "semester": semester, "courses": [
        {"course_code": c, "course_name": f"Course {c}", "credit_hours": 3, "grade": g} for c, g in courses]}


def test_save_a_whole_semester(client):
    headers = student(client, 1)
    res = client.post("/results/semester", headers=headers,
                      json=semester_body([("dipc001", "A"), ("DIPC003", "b+"), ("DIPT001", "C")]))
    assert res.status_code == 201, res.text
    assert res.json()["message"] == "Saved 3 courses."
    semesters = client.get("/results/me", headers=headers).json()["semesters"]
    assert len(semesters) == 1 and len(semesters[0]["results"]) == 3
    assert {r["course_code"] for r in semesters[0]["results"]} == {"DIPC001", "DIPC003", "DIPT001"}
    assert semesters[0]["gpa"] == 3.0


def test_semester_is_all_or_nothing(client):
    headers = student(client, 1)
    twice = client.post("/results/semester", headers=headers, json=semester_body([("DIPC001", "A"), ("dipc001", "B")]))
    assert twice.status_code == 400 and "listed twice" in twice.json()["detail"]
    bad_grade = client.post("/results/semester", headers=headers, json=semester_body([("DIPC001", "A"), ("DIPC003", "Z")]))
    assert bad_grade.status_code == 400
    assert client.get("/results/me", headers=headers).json()["total_results"] == 0

    add_result(client, headers, "DIPC003", "B")
    clash = client.post("/results/semester", headers=headers, json=semester_body([("DIPC001", "A"), ("DIPC003", "A")]))
    assert clash.status_code == 409 and "DIPC003" in clash.json()["detail"]
    assert client.get("/results/me", headers=headers).json()["total_results"] == 1


def test_semester_limits(client):
    headers = student(client, 1)
    assert client.post("/results/semester", headers=headers, json=semester_body([])).status_code == 422
    too_many = semester_body([(f"DIPC0{n:02d}", "A") for n in range(16)])
    assert client.post("/results/semester", headers=headers, json=too_many).status_code == 422
    future = client.post("/results/semester", headers=headers, json=semester_body([("DIPC001", "A")], year="2030/2031"))
    assert future.status_code == 400


def test_admin_correction_confirms_credits(client, admin_headers):
    courses = client.get("/admin/courses", headers=admin_headers).json()["courses"]
    bsit301 = next(c for c in courses if c["code"] == "BSIT301")
    assert bsit301["source"] == "timetable"
    res = client.put(f"/admin/courses/{bsit301['id']}", headers=admin_headers, json={"credit_hours": 4})
    assert res.status_code == 200

    headers = student(client, 1, programme=BSC_IT, level=300, year="2026/2027")
    course = next(c for c in suggest(client, headers, "2026/2027", 1)["courses"] if c["course_code"] == "BSIT301")
    assert course["credit_hours"] == 4 and course["credits_confirmed"] is True


def test_students_cannot_edit_courses(client, student_headers):
    assert client.put("/admin/courses/1", headers=student_headers, json={"credit_hours": 4}).status_code == 403
