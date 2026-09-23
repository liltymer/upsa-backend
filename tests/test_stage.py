"""Academic stage messages on the dashboard."""
from tests.conftest import add_result, login, register
from tests.test_insights import diploma_student

BSC_IT = "Bachelor of Science in Information Technology"


def stage(client, headers, **params):
    return client.get("/insights/me", headers=headers, params=params).json()["stage"]


def test_not_started_then_early(client):
    register(client, programme=BSC_IT, level=100, academic_year="2025/2026")
    headers = login(client)
    assert stage(client, headers)["key"] == "not_started"
    add_result(client, headers, "BIT101", "B", 3, "2025/2026", 1)
    add_result(client, headers, "BIT102", "B", 3, "2025/2026", 1)
    st = stage(client, headers)
    assert st["key"] == "early" and st["title"] == "First year of your degree"
    # 6 credits at 3.0 plus a 6-credit semester: all A gives 3.50, all C gives 2.25
    assert (st["next_semester"]["best"], st["next_semester"]["with_c"]) == (3.5, 2.25)
    assert "(all C's)" in st["messages"][0]


def test_middle(client):
    register(client, programme=BSC_IT, level=200, academic_year="2025/2026")
    headers = login(client)
    for year, sem in [("2024/2025", 1), ("2024/2025", 2), ("2025/2026", 1)]:
        add_result(client, headers, f"BIT{sem}{year[:4]}", "B", 3, year, sem)
    st = stage(client, headers)
    assert st["key"] == "middle" and "Steady grades" in st["messages"][0]


def test_final_year(client):
    register(client, index_number="D1", level=100, academic_year="2025/2026")
    headers = login(client)
    for sem in (1, 2):
        add_result(client, headers, f"DIPT10{sem}", "B", 3, "2025/2026", sem)
    st = stage(client, headers)
    # Diploma: 4 semesters, 2 recorded, so the next two are the final year
    assert st["key"] == "final" and st["finish"]["remaining_credits"] == 6
    assert (st["finish"]["best"], st["finish"]["with_c"]) == (3.5, 2.25)
    assert any("Distinction" in m for m in st["messages"])


def test_complete_diploma_suggests_top_up(client):
    headers = diploma_student(client)
    st = stage(client, headers)
    assert st["key"] == "complete" and "Credit (2.88)" in st["messages"][0]
    assert any("Topping up" in m for m in st["messages"])


def test_top_up_start_and_completed_programme(client):
    headers = diploma_student(client)
    client.post("/enrollments/top-up", headers=headers, json={
        "index_number": "20261234", "programme": BSC_IT, "academic_year": "2026/2027"})
    st = stage(client, headers)
    assert st["key"] == "top_up_start" and "Level 300" in st["title"]
    diploma_id = next(e["id"] for e in client.get("/enrollments/me", headers=headers).json()["enrollments"]
                      if e["award_type"] == "diploma")
    old = stage(client, headers, enrollment_id=diploma_id)
    assert old["key"] == "completed_programme" and "final" in old["messages"][0]


def test_messages_have_no_dashes(client):
    headers = diploma_student(client)
    text = " ".join(stage(client, headers)["messages"])
    assert "—" not in text and "–" not in text
