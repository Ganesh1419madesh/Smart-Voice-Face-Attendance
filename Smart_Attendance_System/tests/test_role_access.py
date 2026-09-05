import pytest
from pathlib import Path

from app import app
from database import initialize_database


@pytest.fixture
def client():
    initialize_database()
    with app.test_client() as client:
        yield client


def test_student_cannot_delete_student(client):
    login = client.post(
        "/api/login",
        json={"username": "student", "password": "student123", "role": "student"},
    )
    assert login.status_code == 200

    response = client.delete("/api/students/BU240501")
    assert response.status_code == 403
    assert response.get_json()["success"] is False


def test_staff_profile_can_be_registered_and_loaded(client):
    login = client.post(
        "/api/login",
        json={"username": "staff", "password": "staff123", "role": "staff"},
    )
    assert login.status_code == 200

    response = client.post(
        "/api/staff/register",
        json={
            "staff_id": "TCH-001",
            "name": "Alice Teacher",
            "department": "Computer Science",
            "email": "alice.teacher@school.edu",
            "phone": "+94 77 123 4567",
        },
    )
    assert response.status_code == 200
    assert response.get_json()["success"] is True

    profile = client.get("/api/staff/me")
    assert profile.status_code == 200
    payload = profile.get_json()
    assert payload["success"] is True
    assert payload["profile"]["name"] == "Alice Teacher"
    assert payload["profile"]["department"] == "Computer Science"


def test_staff_profile_form_uses_post_submission():
    dashboard = Path(__file__).resolve().parents[1] / "frontend" / "dashboard.html"
    html = dashboard.read_text(encoding="utf-8")
    assert 'id="staff-profile-form"' in html
    assert 'method="post"' in html
