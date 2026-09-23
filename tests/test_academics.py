from tests.conftest import add_result


def test_cgpa_and_classification_for_diploma(client, student_headers):
    add_result(client, student_headers, "A1", "A")
    add_result(client, student_headers, "B1", "B")

    cgpa = client.get("/gpa/cgpa", headers=student_headers).json()
    assert cgpa["cgpa"] == 3.5
    assert cgpa["classification"] == "Credit"  # diploma band, not "Second Class Upper"

    risk = client.get("/risk/me", headers=student_headers).json()["risk_analysis"]
    assert risk["classification"] == "Credit"
    assert risk["next_class"] == "Distinction"
    assert risk["gap_to_next_class"] == 0.1


def test_degree_uses_degree_bands(client):
    from tests.conftest import login, register
    register(client, programme="Bachelor of Science in Information Technology")
    headers = login(client)
    add_result(client, headers, "BIT101", "A")
    add_result(client, headers, "BIT102", "B")
    assert client.get("/dashboard/me", headers=headers).json()["classification"] == "Second Class Upper"


def test_gpa_is_truncated_not_rounded(client, student_headers):
    # 56.5 / 20 = 2.825 — UPSA reports 2.82
    for code, credits, grade in [("C1", 3, "C"), ("C2", 3, "C"), ("C3", 3, "A"), ("C4", 3, "A"),
                                 ("C5", 3, "C"), ("C6", 2, "B+"), ("C7", 3, "A")]:
        add_result(client, student_headers, code, grade, credits)
    assert client.get("/gpa/cgpa", headers=student_headers).json()["cgpa"] == 2.82


def test_projection_simulate(client, student_headers):
    add_result(client, student_headers, "A1", "A")
    res = client.post("/projection/simulate", headers=student_headers,
                      json={"projected_courses": [{"credit_hours": 3, "grade_point": 2.0}]})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["current_cgpa"] == 4.0
    assert body["projected_cgpa"] == 3.0


def test_projection_rejects_out_of_range_grade_point(client, student_headers):
    res = client.post("/projection/simulate", headers=student_headers,
                      json={"projected_courses": [{"credit_hours": 3, "grade_point": 9}]})
    assert res.status_code == 422


def test_projection_target(client, student_headers):
    add_result(client, student_headers, "A1", "C+")  # 2.0 over 3 credits
    res = client.get("/projection/target", headers=student_headers,
                     params={"target_cgpa": 3.0, "remaining_credits": 3})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["required_grade_point_average"] == 4.0
    assert body["required_grade"] == "A"
    assert body["achievable"] is True


def test_result_validation(client, student_headers):
    bad_year = client.post("/results/", headers=student_headers, json={
        "course_code": "X", "course_name": "X", "credit_hours": 3, "grade": "A",
        "academic_year": "2019/2020", "semester": 1,
    })
    assert bad_year.status_code == 400  # before the programme started

    add_result(client, student_headers, "DUP1", "A")
    dup = client.post("/results/", headers=student_headers, json={
        "course_code": "dup1", "course_name": "X", "credit_hours": 3, "grade": "B",
        "academic_year": "2025/2026", "semester": 1,
    })
    assert dup.status_code == 409


def test_results_grouped_by_semester(client, student_headers):
    add_result(client, student_headers, "S1", "A", semester=1)
    add_result(client, student_headers, "S2", "B", semester=2)
    body = client.get("/results/me", headers=student_headers).json()
    assert [(s["academic_year"], s["semester"], s["level"]) for s in body["semesters"]] == [
        ("2025/2026", 1, 100), ("2025/2026", 2, 100),
    ]
    assert body["semesters"][1]["cgpa"] == 3.5


def test_transcript_pdf_download(client, student_headers):
    add_result(client, student_headers, "A1", "A")
    res = client.get("/transcript/download", headers=student_headers)
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert res.content.startswith(b"%PDF")
    assert 'filename="transcript_10212345.pdf"' in res.headers["content-disposition"]


def test_reference_data_lists_current_academic_year(client):
    body = client.get("/reference/academic").json()
    assert body["academic_years"][0] == body["current_academic_year"]
    assert {b["label"] for b in body["classification_bands"]["diploma"]} == {"Distinction", "Credit", "Pass", "Fail"}
