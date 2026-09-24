"""Unofficial transcript PDF and a top-up student's full academic history."""
import base64
import re
import zlib

from tests.conftest import add_result
from tests.test_topup import BSC_IT, DEGREE_INDEX, enter_diploma, register_diploma_student


def pdf_text(content: bytes) -> str:
    """Page content streams, decompressed when reportlab compressed them."""
    text = content.decode("latin-1")
    for stream in re.findall(rb"stream\r?\n(.*?)endstream", content, re.S):
        try:
            data = stream.strip()
            if data.endswith(b"~>"):
                data = base64.a85decode(data[:-2])
            text += zlib.decompress(data).decode("latin-1")
        except (zlib.error, ValueError):
            pass
    return text


def top_up_student(client):
    headers = register_diploma_student(client)
    enter_diploma(client, headers)
    res = client.post("/enrollments/top-up", headers=headers, json={
        "index_number": DEGREE_INDEX, "programme": BSC_IT, "academic_year": "2026/2027"})
    assert res.status_code == 201, res.text
    add_result(client, headers, "BSIT301", "A", academic_year="2026/2027", semester=1)
    return headers


def test_pdf_is_marked_unofficial_and_numbered(client, student_headers):
    add_result(client, student_headers, "DIPC001", "A")
    res = client.get("/transcript/download", headers=student_headers)
    assert res.status_code == 200 and res.content.startswith(b"%PDF")
    text = pdf_text(res.content)
    assert "UNOFFICIAL" in text
    assert "Page 1 of 1" in text
    assert "Grading Key" in text and "Distinction" in text


def test_history_lists_each_programme_with_its_own_cgpa(client):
    headers = top_up_student(client)
    programmes = client.get("/transcript/history", headers=headers).json()["programmes"]
    assert [p["award_type"] for p in programmes] == ["diploma", "degree"]
    assert programmes[0]["classification"] == "Credit"
    assert programmes[1]["cgpa"] == 4.0 and programmes[1]["index_number"] == DEGREE_INDEX


def test_full_history_pdf(client):
    headers = top_up_student(client)
    res = client.get("/transcript/download", headers=headers, params={"scope": "all"})
    assert res.status_code == 200
    assert f'filename="transcript_full_history_{DEGREE_INDEX}.pdf"' in res.headers["content-disposition"]
    text = pdf_text(res.content)
    assert "Part 1 of 2: Diploma" in text and "Part 2 of 2: Degree" in text
    # Both class keys, since the document covers a diploma and a degree
    assert "Diploma class" in text and "Degree class" in text


def test_full_history_needs_results_and_login(client, student_headers):
    assert client.get("/transcript/download", headers=student_headers, params={"scope": "all"}).status_code == 400
    assert client.get("/transcript/history").status_code == 401
    assert client.get("/transcript/download", headers=student_headers, params={"scope": "x"}).status_code == 422
