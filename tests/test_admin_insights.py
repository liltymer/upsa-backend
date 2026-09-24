"""Admin insights: activity, what needs attention, hardest courses and the top-up pipeline."""
from tests.conftest import add_result, login, register
from tests.test_topup import enter_diploma, register_diploma_student


def insights(client, headers):
    res = client.get("/admin/insights", headers=headers)
    assert res.status_code == 200, res.text
    return res.json()


def titles(body):
    return {a["title"] for a in body["attention"]}


def test_activity_counts_signups_results_and_sign_ins(client, admin_headers, student_headers):
    add_result(client, student_headers, "DIPC001", "A")
    body = insights(client, admin_headers)["activity"]
    assert body["signups_7d"] == 1 and body["results_7d"] == 1 and body["active_7d"] == 1
    assert len(body["weekly"]) == 8 and body["weekly"][-1]["results"] == 1


def test_users_list_has_join_and_last_active_dates(client, admin_headers, student_headers):
    ama = next(u for u in client.get("/admin/users", headers=admin_headers).json()["students"] if u["email"] == "ama@gmail.com")
    assert ama["joined"] and ama["last_active"]


def test_email_sender_warning(client, admin_headers, monkeypatch):
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    assert "Password reset emails are off" in titles(insights(client, admin_headers))
    monkeypatch.setenv("RESEND_API_KEY", "re_test")
    monkeypatch.delenv("EMAIL_FROM", raising=False)
    assert "Password reset emails only reach you" in titles(insights(client, admin_headers))
    monkeypatch.setenv("EMAIL_FROM", "GradeIQ UPSA <no-reply@gradeiq.app>")
    assert not any("Password reset" in t for t in titles(insights(client, admin_headers)))


def test_attention_flags_unknown_codes_and_no_announcement(client, admin_headers, student_headers):
    add_result(client, student_headers, "ZZQ101", "B")
    body = insights(client, admin_headers)
    unknown = next(a for a in body["attention"] if a["title"].startswith("Course codes students typed"))
    assert unknown["count"] == 1
    assert "No announcement is showing" in titles(body)
    client.post("/admin/announcements", headers=admin_headers, json={"title": "Hello", "message": "Welcome back"})
    assert "No announcement is showing" not in titles(insights(client, admin_headers))


def test_hardest_courses_need_five_students(client, admin_headers):
    for n in range(5):
        email = f"h{n}@gmail.com"
        register(client, email=email, index_number=f"1050000{n}")
        add_result(client, login(client, email=email), "DIPC005", "F" if n < 3 else "B")
        if n == 3:
            assert insights(client, admin_headers)["hardest_courses"] == []
    hardest = insights(client, admin_headers)["hardest_courses"]
    assert hardest[0]["course_code"] == "DIPC005" and hardest[0]["students"] == 5 and hardest[0]["fail_rate"] == 0.6


def test_top_up_pipeline(client, admin_headers):
    enter_diploma(client, register_diploma_student(client))
    assert insights(client, admin_headers)["top_up"] == {"topped_up": 0, "diploma_finished_not_topped_up": 1, "diploma_in_progress": 0}


def test_insights_need_admin(client, student_headers):
    assert client.get("/admin/insights", headers=student_headers).status_code == 403
