"""The read-only trail API over the saved, masked runs."""

import re

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_health_counts_the_runs():
    r = client.get("/api/health")
    assert r.status_code == 200 and r.json()["ok"] and r.json()["runs"] > 0


def test_cases_start_with_the_featured_trail():
    cases = client.get("/api/cases").json()
    assert cases[0]["slug"] == "93-list"
    assert {c["era"] for c in cases} <= {"2025", "2026", "discovered"}


def test_summary_numbers_are_the_facts_file():
    s = client.get("/api/summary").json()
    m, facts = s["monitor_2026"], s["facts"]["monitor_2026"]
    assert m["copies"] == facts["copies"] == m["corrected"] + m["dropped"] + m["still_held"]
    assert m["cases"] == len(facts["cases"])
    assert s["featured"]["slug"] == "93-list"


def test_every_case_opens_as_a_trail():
    for c in client.get("/api/cases").json():
        t = client.get(f"/api/trails/{c['slug']}")
        assert t.status_code == 200 and t.json()["summary"]["slug"] == c["slug"]


def test_odd_slugs_are_refused():
    assert client.get("/api/trails/..%2Fsecrets").status_code == 404
    assert client.get("/api/trails/NOT-A-CASE").status_code == 404
    assert client.get("/api/trails/no-such-case").status_code == 404


def test_no_email_in_any_response():
    email = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
    for path in ("/api/cases", "/api/summary", "/api/score", "/api/alive", "/api/discover", "/api/trails/93-list"):
        assert not email.search(client.get(path).text), path
