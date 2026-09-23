"""Dashboard insights, checked against a real UPSA diploma transcript."""
from tests.conftest import add_result, login, register
from tests.test_topup import DIPLOMA_INDEX, DIPLOMA_TRANSCRIPT, enter_diploma


def diploma_student(client):
    assert register(client, index_number=DIPLOMA_INDEX, level=200, academic_year="2025/2026").status_code == 201
    headers = login(client)
    enter_diploma(client, headers)
    return headers


def test_summary_matches_transcript(client):
    headers = diploma_student(client)
    body = client.get("/insights/me", headers=headers).json()
    s = body["summary"]
    assert (s["cgpa"], s["classification"], s["next_class"], s["gap_to_next_class"]) == (2.88, "Credit", "Distinction", 0.72)
    assert (s["credits_completed"], s["courses_completed"], s["semesters_completed"]) == (72, 24, 4)
    assert (s["latest_gpa"], s["previous_gpa"], s["direction"]) == (3.13, 2.82, "improving")
    assert s["weakest_semester"]["gpa"] == 2.58 and s["best_semester"]["gpa"] == 3.13
    assert [h["cgpa"] for h in body["history"]] == [3.00, 2.77, 2.79, 2.88]


def test_courses_pulling_down_and_strongest(client):
    headers = diploma_student(client)
    body = client.get("/insights/me", headers=headers).json()
    worst = body["pulling_down"][0]
    assert worst["grade"] == "C-" and worst["impact"] < 0
    assert all(c["impact"] < 0 for c in body["pulling_down"])
    assert len(body["pulling_down"]) <= 5
    assert body["strongest"][0]["grade"] == "A"
    assert body["strongest"][0]["credit_hours"] == 4  # the 4-credit project comes first among the A grades


def test_areas_and_grade_spread(client):
    headers = diploma_student(client)
    body = client.get("/insights/me", headers=headers).json()
    areas = {a["area"]: a for a in body["areas"]}
    assert set(areas) == {"DIPC", "DIPT", "DIPL"}
    assert sum(a["credits"] for a in areas.values()) == 72
    spread = {g["grade"]: g["count"] for g in body["grade_distribution"]}
    assert spread["A"] == 8 and sum(spread.values()) == 24


def test_target_uses_estimate_or_override(client):
    headers = diploma_student(client)
    body = client.get("/insights/me", headers=headers).json()
    # A diploma runs four semesters and all four are recorded
    assert body["estimate"]["remaining_semesters"] == 0 and body["target"] is None

    body = client.get("/insights/me", headers=headers, params={"remaining_credits": 30}).json()
    t = body["target"]
    assert t["target_class"] == "Distinction" and t["achievable"] is False
    assert t["max_possible_cgpa"] == 3.21 and t["remaining_credits_estimated"] is False
    assert any(a["kind"] == "target" and "Protect" in a["title"] for a in body["actions"])


def test_achievable_target_and_drop_warning(client):
    register(client, programme="Bachelor of Science in Information Technology", level=100, academic_year="2025/2026")
    headers = login(client)
    add_result(client, headers, "BIT101", "A", 3, "2025/2026", 1)
    add_result(client, headers, "BIT102", "B", 3, "2025/2026", 1)
    add_result(client, headers, "BIT103", "C", 3, "2025/2026", 2)
    body = client.get("/insights/me", headers=headers).json()
    assert body["estimate"]["total_semesters"] == 8 and body["estimate"]["remaining_semesters"] == 6
    t = body["target"]
    assert t["target_class"] == "Second Class Upper" and t["achievable"] is True and t["required_grade"]
    kinds = [a["kind"] for a in body["actions"]]
    assert "target" in kinds and "trend" in kinds and len(kinds) <= 3


def test_empty_programme(client):
    register(client)
    headers = login(client)
    body = client.get("/insights/me", headers=headers).json()
    assert body["has_results"] is False
    assert body["actions"][0]["kind"] == "start"
    assert body["pulling_down"] == [] and body["target"] is None


def test_no_em_dashes_in_messages(client):
    headers = diploma_student(client)
    risk = client.get("/risk/me", headers=headers).json()["risk_analysis"]
    insights = client.get("/insights/me", headers=headers, params={"remaining_credits": 30}).json()
    text = " ".join(risk["alerts"]) + " ".join(a["title"] + a["body"] for a in insights["actions"])
    assert "—" not in text and "–" not in text


def test_other_students_programme_is_private(client):
    diploma_student(client)
    register(client, email="b@gmail.com", index_number="B2")
    other = login(client, email="b@gmail.com")
    assert client.get("/insights/me", headers=other, params={"enrollment_id": 1}).status_code == 404
    assert DIPLOMA_TRANSCRIPT  # fixture data shared with test_topup
