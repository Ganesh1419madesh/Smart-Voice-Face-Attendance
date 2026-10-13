import pytest
from pathlib import Path
from types import SimpleNamespace
import sys

from app import app
import app as app_module
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


def test_staff_sidebar_opens_staff_directory():
    project = Path(__file__).resolve().parents[1]
    html = (project / "frontend" / "dashboard.html").read_text(encoding="utf-8")
    script = (project / "frontend" / "js" / "app.js").read_text(encoding="utf-8")
    assert 'id="staff-list-page"' in html
    assert 'id="staff-rows"' in html
    assert "'staff-list': 'staff-list-page'" in script
    assert "if (button.dataset.page === 'staff-list') await loadStaff();" in script


def test_student_my_attendance_opens_personal_records_page():
    project = Path(__file__).resolve().parents[1]
    html = (project / "frontend" / "dashboard.html").read_text(encoding="utf-8")
    script = (project / "frontend" / "js" / "app.js").read_text(encoding="utf-8")
    assert "{ page: 'my-attendance', label: 'My Attendance' }" in script
    assert "'my-attendance': 'my-attendance-page'" in script
    assert 'id="my-attendance-page"' in html
    assert "if (button.dataset.page === 'my-attendance') await loadMyAttendance();" in script


def test_attendance_camera_starts_on_button_with_quick_constraints():
    project = Path(__file__).resolve().parents[1]
    html = (project / "frontend" / "dashboard.html").read_text(encoding="utf-8")
    script = (project / "frontend" / "js" / "app.js").read_text(encoding="utf-8")
    assert 'id="start-camera"' in html
    assert "$('#start-camera').addEventListener('click', startCamera);" in script
    assert "width: { ideal: 640 }, height: { ideal: 480 }" in script


def test_admin_can_delete_staff_profile(client):
    login = client.post(
        "/api/login",
        json={"username": "admin", "password": "admin123", "role": "admin"},
    )
    assert login.status_code == 200

    response = client.delete("/api/staff/TCH-DELETE-TEST")
    assert response.status_code == 404


def test_staff_cannot_delete_staff_profile(client):
    login = client.post(
        "/api/login",
        json={"username": "staff", "password": "staff123", "role": "staff"},
    )
    assert login.status_code == 200

    response = client.delete("/api/staff/TCH-001")
    assert response.status_code == 403


def test_auto_attendance_skips_voice_recognition_by_default(client, monkeypatch):
    login = client.post(
        "/api/login",
        json={"username": "admin", "password": "admin123", "role": "admin"},
    )
    assert login.status_code == 200

    monkeypatch.setattr(
        app_module, "get_student", lambda student_id: {
            "student_id": student_id, "name": "Test Student"
        }
    )
    monkeypatch.setattr(
        app_module, "mark_attendance", lambda *args, **kwargs: {
            "success": True, "message": "Time-in recorded", "action": "in"
        }
    )
    monkeypatch.setattr(app_module, "save_attendance_photo", lambda *args: "test.jpg")
    monkeypatch.setitem(
        sys.modules,
        "voice_recognition",
        SimpleNamespace(recognize_voice=lambda: pytest.fail("voice recognition should be skipped")),
    )

    response = client.post(
        "/api/attendance/auto",
        json={"student_id": "FAST-001", "photo": "data:image/jpeg;base64,AA=="},
    )

    assert response.status_code == 200
    assert response.get_json()["voice"] is None
