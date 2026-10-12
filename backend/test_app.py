import pytest

import backend.app as app_module


@pytest.fixture()
def client(tmp_path, monkeypatch):
    database = tmp_path / "test.sqlite3"
    monkeypatch.setattr(app_module, "DATABASE", database)
    app_module.init_db()
    app_module.seed_db()
    app_module.app.config.update(TESTING=True)
    with app_module.app.test_client() as test_client:
        yield test_client


def login(client, email, password):
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return {"X-User-Id": response.json["user"]["id"]}


def test_login_and_role_protection(client):
    admin_headers = login(client, "admin@northbridge.edu", "admin-demo")
    assert client.get("/api/analytics", headers=admin_headers).status_code == 200
    student_headers = login(client, "student@northbridge.edu", "student-demo")
    assert client.get("/api/analytics", headers=student_headers).status_code == 403


def test_student_submission_gets_rule_based_triage(client):
    headers = login(client, "student@northbridge.edu", "student-demo")
    response = client.post("/api/complaints", headers=headers, json={"title": "Water leak near lab", "description": "Urgent water leak by the entrance", "location": "Science Block"})
    assert response.status_code == 201
    assert response.json["ai"]["category"] == "Water Supply"
    assert response.json["ai"]["priority"] in {"High", "Critical"}


def test_admin_can_export_csv(client):
    headers = login(client, "admin@northbridge.edu", "admin-demo")
    response = client.get("/api/reports/complaints.csv", headers=headers)
    assert response.status_code == 200
    assert "text/csv" in response.content_type
    assert "public_id" in response.text


def test_assignment_and_status_history_are_persisted(client):
    admin_headers = login(client, "admin@northbridge.edu", "admin-demo")
    response = client.patch("/api/complaints/1", headers=admin_headers, json={"status": "Resolved", "assigned_team": "Facilities Response", "resolution_notes": "Leak repaired"})
    assert response.status_code == 200
    history = client.get("/api/complaints/1/history", headers=admin_headers)
    assert history.status_code == 200
    assert history.json["items"][-1]["status"] == "Resolved"
    notifications = client.get("/api/notifications", headers=login(client, "admin@northbridge.edu", "admin-demo"))
    assert notifications.status_code == 200


def test_duplicate_reports_are_grouped(client):
    headers = login(client, "student@northbridge.edu", "student-demo")
    payload = {"title": "Wi-Fi disconnects in engineering", "description": "Internet connection drops in the engineering building", "location": "Engineering Block"}
    first = client.post("/api/complaints", headers=headers, json=payload)
    second = client.post("/api/complaints", headers=headers, json=payload)
    assert first.status_code == 201 and second.status_code == 201
    assert second.json["complaint"]["duplicate_group_id"] is not None


def test_ml_metrics_are_admin_only(client):
    admin_headers = login(client, "admin@northbridge.edu", "admin-demo")
    metrics = client.get("/api/ml/metrics", headers=admin_headers)
    assert metrics.status_code == 200
    assert metrics.json["training_examples"] >= 16
    assert client.get("/api/ml/metrics", headers=login(client, "student@northbridge.edu", "student-demo")).status_code == 403
