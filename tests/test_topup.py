"""
Diploma → degree top-up journey.

Reference data: a real UPSA Diploma in Information Technology Management
transcript (AUG 2024 – AUG 2026). UPSA's printed figures are asserted below.
"""
from tests.conftest import add_result, login, register

DIPLOMA_TRANSCRIPT = {
    ("2024/2025", 1): [("DIPC005", 3, "C-"), ("DIPC009", 3, "B+"), ("DIPT001", 3, "A"),
                       ("DIPT003", 3, "A"), ("DIPC003", 3, "B-")],
    ("2024/2025", 2): [("DIPC014", 3, "B-"), ("DIPC006", 3, "C+"), ("DIPT002", 3, "B-"),
                       ("DIPT004", 3, "A"), ("DIPT006", 3, "C+"), ("DIPT008", 3, "B-")],
    ("2025/2026", 1): [("DIPL055", 3, "C"), ("DIPT059", 3, "C"), ("DIPT057", 3, "A"), ("DIPT055", 3, "A"),
                       ("DIPT053", 3, "C"), ("DIPT051", 2, "B+"), ("DIPC053", 3, "A")],
    ("2025/2026", 2): [("DIPT052", 3, "C-"), ("DIPT054", 3, "A"), ("DIPT056", 3, "B+"),
                       ("DIPT058", 3, "B+"), ("DIPT062", 3, "B-"), ("DIPT050", 4, "A")],
}

# (TCR, TGP, GPA, CGPA) exactly as printed on the UPSA transcript
UPSA_FIGURES = {
    ("2024/2025", 1): (15, 45.0, 3.00, 3.00),
    ("2024/2025", 2): (18, 46.5, 2.58, 2.77),
    ("2025/2026", 1): (20, 56.5, 2.82, 2.79),
    ("2025/2026", 2): (19, 59.5, 3.13, 2.88),
}

DIPLOMA_INDEX = "10324631"
DEGREE_INDEX = "20261234"
BSC_IT = "Bachelor of Science in Information Technology"


def enter_diploma(client, headers):
    for (academic_year, semester), rows in DIPLOMA_TRANSCRIPT.items():
        for code, credits, grade in rows:
            add_result(client, headers, code, grade, credits, academic_year, semester)


def register_diploma_student(client):
    res = register(client, index_number=DIPLOMA_INDEX, level=200, academic_year="2025/2026")
    assert res.status_code == 201, res.text
    return login(client)


def test_diploma_figures_match_upsa_transcript(client):
    headers = register_diploma_student(client)
    enter_diploma(client, headers)

    transcript = client.get("/transcript/me", headers=headers).json()
    for sem in transcript["transcript"]:
        tcr, tgp, gpa, cgpa = UPSA_FIGURES[(sem["academic_year"], sem["semester"])]
        assert (sem["total_credits"], sem["total_grade_points"], sem["semester_gpa"], sem["cgpa"]) == (tcr, tgp, gpa, cgpa)

    assert transcript["cgpa"] == 2.88
    assert transcript["classification"] == "Credit"
    assert [s["level"] for s in transcript["transcript"]] == [100, 100, 200, 200]


def test_top_up_keeps_diploma_and_starts_fresh_cgpa(client):
    headers = register_diploma_student(client)
    enter_diploma(client, headers)

    res = client.post("/enrollments/top-up", headers=headers, json={
        "index_number": DEGREE_INDEX, "programme": BSC_IT, "academic_year": "2026/2027",
    })
    assert res.status_code == 201, res.text

    programmes = {e["award_type"]: e for e in res.json()["enrollments"]}
    diploma, degree = programmes["diploma"], programmes["degree"]
    assert diploma["status"] == "completed" and not diploma["is_current"]
    assert diploma["cgpa"] == 2.88 and diploma["classification"] == "Credit"
    assert degree["is_current"] and degree["is_top_up"]
    assert degree["cgpa"] == 0.0 and degree["current_level"] == 300

    # Fresh degree CGPA — diploma results are not included
    add_result(client, headers, "BIT301", "B", academic_year="2026/2027")
    dash = client.get("/dashboard/me", headers=headers).json()
    assert dash["index_number"] == DEGREE_INDEX
    assert dash["cgpa"] == 3.0
    assert dash["classification"] == "Second Class Upper"
    assert dash["other_programmes"][0]["cgpa"] == 2.88

    # The diploma is still fully viewable
    diploma_transcript = client.get(
        "/transcript/me", headers=headers, params={"enrollment_id": diploma["id"]}
    ).json()
    assert diploma_transcript["index_number"] == DIPLOMA_INDEX
    assert diploma_transcript["cgpa"] == 2.88
    pdf = client.get("/transcript/download", headers=headers, params={"enrollment_id": diploma["id"]})
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")

    # Typos in the completed diploma can still be fixed
    diploma_results = client.get(
        "/results/me", headers=headers, params={"enrollment_id": diploma["id"]}
    ).json()["results"]
    first = diploma_results[0]
    fixed = client.put(f"/results/{first['result_id']}", headers=headers, json={"course_name": "Corrected Title"})
    assert fixed.status_code == 200, fixed.text


def test_login_with_either_index_number(client):
    headers = register_diploma_student(client)
    client.post("/enrollments/top-up", headers=headers, json={
        "index_number": DEGREE_INDEX, "programme": BSC_IT, "academic_year": "2026/2027",
    })
    for username in (DIPLOMA_INDEX, DEGREE_INDEX, "ama@gmail.com"):
        res = client.post("/auth/login", data={"username": username, "password": "Correct-Horse-1"})
        assert res.status_code == 200, username


def test_top_up_rejects_diploma_programme_and_taken_index(client):
    headers = register_diploma_student(client)
    taken = client.post("/enrollments/top-up", headers=headers, json={
        "index_number": DIPLOMA_INDEX, "programme": BSC_IT, "academic_year": "2026/2027",
    })
    assert taken.status_code == 409

    bad_level = client.post("/enrollments/top-up", headers=headers, json={
        "index_number": "NEW1", "programme": "Diploma in Marketing", "academic_year": "2026/2027",
    })
    assert bad_level.status_code == 400  # a diploma has no Level 300


def test_undo_accidental_top_up(client):
    headers = register_diploma_student(client)
    enrollments = client.post("/enrollments/top-up", headers=headers, json={
        "index_number": DEGREE_INDEX, "programme": BSC_IT, "academic_year": "2026/2027",
    }).json()["enrollments"]
    degree = next(e for e in enrollments if e["is_current"])

    res = client.delete(f"/enrollments/{degree['id']}", headers=headers)
    assert res.status_code == 200, res.text
    remaining = res.json()["enrollments"]
    assert len(remaining) == 1
    assert remaining[0]["is_current"] and remaining[0]["status"] == "active"


def test_register_as_top_up_with_previous_diploma(client):
    res = register(
        client, index_number=DEGREE_INDEX, programme=BSC_IT, level=300,
        academic_year="2026/2027", is_top_up=True,
        previous_programme={
            "index_number": DIPLOMA_INDEX,
            "programme": "Diploma in Information Technology Management",
            "start_academic_year": "2024/2025",
        },
    )
    assert res.status_code == 201, res.text
    headers = login(client)

    enrollments = client.get("/enrollments/me", headers=headers).json()["enrollments"]
    assert [e["award_type"] for e in enrollments] == ["degree", "diploma"]
    diploma = enrollments[1]

    # Diploma history can be entered afterwards against the previous programme
    for (academic_year, semester), rows in DIPLOMA_TRANSCRIPT.items():
        for code, credits, grade in rows:
            add_result(client, headers, code, grade, credits, academic_year, semester,
                       enrollment_id=diploma["id"])

    by_id = {e["id"]: e for e in client.get("/enrollments/me", headers=headers).json()["enrollments"]}
    assert by_id[diploma["id"]]["cgpa"] == 2.88
    assert client.get("/gpa/cgpa", headers=headers).json()["cgpa"] == 0.0  # degree untouched


def test_move_results_between_programmes(client):
    # Student who typed diploma results into their degree
    register(client, programme=BSC_IT, level=300, academic_year="2026/2027", is_top_up=True)
    headers = login(client)
    moved_ids = [
        add_result(client, headers, "DIPT001", "A", academic_year="2026/2027")["result_id"],
        add_result(client, headers, "DIPT003", "B", academic_year="2026/2027")["result_id"],
    ]
    add_result(client, headers, "BIT301", "C+", academic_year="2026/2027")

    diploma = client.post("/enrollments/previous", headers=headers, json={
        "programme": "Diploma in Information Technology Management", "start_academic_year": "2024/2025",
    }).json()["enrollments"][1]

    res = client.post("/results/move", headers=headers, json={"result_ids": moved_ids, "enrollment_id": diploma["id"]})
    assert res.status_code == 200, res.text
    assert res.json()["enrollment"]["cgpa"] == 3.5
    assert client.get("/gpa/cgpa", headers=headers).json()["cgpa"] == 2.0


def test_link_second_account(client):
    # Old diploma account
    register(client, email="old@gmail.com", index_number=DIPLOMA_INDEX, level=200)
    old_headers = login(client, email="old@gmail.com")
    add_result(client, old_headers, "DIPT001", "A", academic_year="2025/2026")

    # New account created for the top-up
    register(client, email="new@gmail.com", index_number=DEGREE_INDEX, programme=BSC_IT,
             level=300, academic_year="2026/2027", is_top_up=True)
    new_headers = login(client, email="new@gmail.com")

    wrong = client.post("/enrollments/link-account", headers=new_headers,
                        json={"email": "old@gmail.com", "password": "not-the-password"})
    assert wrong.status_code == 400

    res = client.post("/enrollments/link-account", headers=new_headers,
                      json={"email": "old@gmail.com", "password": "Correct-Horse-1"})
    assert res.status_code == 200, res.text
    enrollments = res.json()["enrollments"]
    current = [e for e in enrollments if e["is_current"]]
    assert len(current) == 1 and current[0]["index_number"] == DEGREE_INDEX
    old = next(e for e in enrollments if e["index_number"] == DIPLOMA_INDEX)
    assert old["status"] == "completed" and old["cgpa"] == 4.0

    # Old login is gone; the diploma index now signs in to the merged account
    assert client.post("/auth/login", data={"username": "old@gmail.com", "password": "Correct-Horse-1"}).status_code == 401
    assert client.post("/auth/login", data={"username": DIPLOMA_INDEX, "password": "Correct-Horse-1"}).status_code == 200


def test_cannot_reach_another_students_programme(client):
    register(client, email="a@gmail.com", index_number="A1")
    register(client, email="b@gmail.com", index_number="B1")
    a = login(client, email="a@gmail.com")
    b = login(client, email="b@gmail.com")
    b_enrollment = client.get("/enrollments/me", headers=b).json()["enrollments"][0]["id"]
    b_result = add_result(client, b, "X1", "A")["result_id"]

    assert client.get("/transcript/me", headers=a, params={"enrollment_id": b_enrollment}).status_code == 404
    assert client.get("/results/me", headers=a, params={"enrollment_id": b_enrollment}).status_code == 404
    assert client.put(f"/results/{b_result}", headers=a, json={"grade": "F"}).status_code == 404
    assert client.post("/results/move", headers=a, json={"result_ids": [b_result], "enrollment_id": b_enrollment}).status_code == 404
    assert client.patch(f"/enrollments/{b_enrollment}", headers=a, json={"programme": "Hacked"}).status_code == 404


def test_top_up_can_join_at_level_200(client):
    res = register(client, index_number="20269999", programme=BSC_IT, level=200,
                   academic_year="2026/2027", is_top_up=True, entry_level=200)
    assert res.status_code == 201, res.text
    headers = login(client)
    current = client.get("/enrollments/me", headers=headers).json()["enrollments"][0]
    assert (current["entry_level"], current["current_level"], current["is_top_up"]) == (200, 200, True)

    # Level 100 is not a valid top-up entry
    bad = register(client, email="x@gmail.com", index_number="X1", programme=BSC_IT, level=100,
                   academic_year="2026/2027", is_top_up=True, entry_level=100)
    assert bad.status_code == 422


def test_reference_lists_official_programmes(client):
    body = client.get("/reference/academic").json()
    names = {p["name"] for p in body["programmes"]}
    assert len([p for p in body["programmes"] if p["award_type"] == "diploma"]) == 5
    assert len([p for p in body["programmes"] if p["award_type"] == "degree"]) == 17
    assert "Bachelor of Science in Applied Statistics" in names
    assert body["top_up_entry_levels"] == [200, 300]


def test_typed_diploma_name_is_detected(client):
    res = register(client, programme="Tertiary Diploma in Accounting", level=100)
    assert res.status_code == 201, res.text
    headers = login(client)
    assert client.get("/enrollments/me", headers=headers).json()["enrollments"][0]["award_type"] == "diploma"
