"""
app.py - Flask API server for Smart Attendance System
"""

import os
import sys
import csv
import io
import base64
from datetime import date, datetime

from functools import wraps

from flask import (Flask, request, jsonify, send_from_directory,
                   send_file, session)
from flask_cors import CORS

# Ensure project root on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import BASE_DIR, WORKING_HOURS_START
from database import (
    initialize_database, verify_user,
    update_user_password,
    get_summary_stats, get_attendance_today, get_attendance_by_date,
    get_attendance_range, get_all_students, search_students,
    delete_student, add_student, get_student,
    update_student, get_student_id_for_username, link_student_to_username,
    mark_attendance, mark_checkout, save_attendance_photo,
    save_staff_profile, get_staff_profile_by_username, get_all_staff,
)

# ── App setup ────────────────────────────────────────────────────────────────
app = Flask(__name__,
            static_folder=os.path.join(BASE_DIR, "frontend"),
            static_url_path="")
app.secret_key = "smart-attendance-secret-key-2024"
CORS(app)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user" not in session:
            return jsonify({"success": False, "message": "Authentication required."}), 401
        return view(*args, **kwargs)
    return wrapped


def role_required(*allowed_roles):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            role = session.get("role")
            if "user" not in session:
                return jsonify({"success": False, "message": "Authentication required."}), 401
            if not allowed_roles or role not in allowed_roles:
                return jsonify({"success": False, "message": "Forbidden: you do not have permission to access this resource."}), 403
            return view(*args, **kwargs)
        return wrapped
    return decorator

PHOTOS_DIR = os.path.join(BASE_DIR, "photos")
os.makedirs(PHOTOS_DIR, exist_ok=True)


# ── Frontend routes ──────────────────────────────────────────────────────────

@app.route("/")
def serve_login():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/dashboard")
def serve_dashboard():
    return send_from_directory(app.static_folder, "dashboard.html")


# ── API: Auth ────────────────────────────────────────────────────────────────

@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json(force=True)
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    role = data.get("role", "").strip().lower()

    if not username or not password or role not in {"admin", "staff", "student"}:
        return jsonify({"success": False, "message": "Please enter username, password, and role."}), 400

    if verify_user(username, password, role):
        session["user"] = username
        session["role"] = role
        return jsonify({"success": True, "message": "Login successful.",
                        "user": username, "role": role})
    else:
        return jsonify({"success": False, "message": "Invalid username or password."}), 401


@app.route("/api/change-password", methods=["POST"])
@login_required
def api_change_password():
    data = request.get_json(force=True)
    current_password = (data.get("current_password") or "").strip()
    new_password = (data.get("new_password") or "").strip()
    username = session.get("user", "")
    role = session.get("role")

    if not current_password or not new_password:
        return jsonify({"success": False, "message": "Enter your current and new passwords."}), 400
    if len(new_password) < 6:
        return jsonify({"success": False, "message": "The new password must be at least 6 characters."}), 400
    if not verify_user(username, current_password, role):
        return jsonify({"success": False, "message": "Current password is incorrect."}), 400
    if not update_user_password(username, new_password):
        return jsonify({"success": False, "message": "User account was not found."}), 404
    return jsonify({"success": True, "message": "Password changed successfully."})


@app.route("/api/session", methods=["GET"])
@login_required
def api_session():
    user = session.get("user")
    role = session.get("role")
    profile = None
    if role == "staff":
        profile = get_staff_profile_by_username(user)
    return jsonify({"success": True, "user": user, "role": role, "profile": profile})


@app.route("/api/staff/me", methods=["GET"])
@login_required
@role_required("staff", "admin")
def api_staff_me():
    user = session.get("user")
    role = session.get("role")
    if role == "staff":
        profile = get_staff_profile_by_username(user)
        if not profile:
            return jsonify({"success": False, "message": "No teacher profile found. Please register your profile first.", "profile": None})
        return jsonify({"success": True, "profile": {**profile, "username": user, "role": "staff"}})
    return jsonify({"success": True, "profile": {"username": user, "name": "Administrator", "department": "Administration", "designation": "Admin", "email": "", "phone": ""}})


@app.route("/api/staff/register", methods=["POST"])
@login_required
@role_required("staff", "admin")
def api_staff_register():
    data = request.get_json(force=True)
    username = (data.get("username") or session.get("user", "")).strip()
    staff_id = data.get("staff_id", "").strip()
    name = data.get("name", "").strip()
    department = data.get("department", "").strip()
    email = data.get("email", "").strip()
    phone = data.get("phone", "").strip()
    designation = data.get("designation", "Teacher").strip() or "Teacher"

    if session.get("role") == "staff" and username != session.get("user"):
        return jsonify({"success": False, "message": "You can only register your own teacher profile."}), 403

    if not username or not staff_id or not name or not department:
        return jsonify({"success": False, "message": "Teacher ID, name, and department are required."}), 400

    ok = save_staff_profile(username, staff_id, name, department, email, phone, designation)
    if ok:
        return jsonify({"success": True, "message": "Teacher profile saved successfully.", "profile": {"username": username, "staff_id": staff_id, "name": name, "department": department, "email": email, "phone": phone, "designation": designation}})
    return jsonify({"success": False, "message": "This teacher ID or username is already in use."}), 409


@app.route("/api/student/me", methods=["GET", "PUT"])
@login_required
@role_required("student")
def api_student_me():
    username = session.get("user")
    student_id = get_student_id_for_username(username)
    if request.method == "PUT":
        data = request.get_json(force=True)
        requested_id = (data.get("student_id") or student_id or "").strip()
        if not requested_id:
            return jsonify({"success": False, "message": "Student ID is required."}), 400
        if student_id and requested_id != student_id:
            return jsonify({"success": False, "message": "You cannot change the student account ID."}), 403
        student = get_student(requested_id)
        if not student:
            return jsonify({"success": False, "message": "Student ID was not found. Ask an administrator to register you first."}), 404
        if not student_id and not link_student_to_username(username, requested_id):
            return jsonify({"success": False, "message": "This student ID is already linked to another account."}), 409
        update_student(requested_id, name=data.get("name", "").strip(),
                       department=data.get("department", "").strip(),
                       course=data.get("course", "").strip(),
                       year=data.get("year", 1), email=data.get("email", "").strip(),
                       phone=data.get("phone", "").strip())
        student = get_student(requested_id)
        return jsonify({"success": True, "message": "Student profile updated successfully.", "profile": student})

    if not student_id:
        return jsonify({"success": False, "message": "No student profile is linked to this account.", "profile": None})
    student = get_student(student_id)
    if not student:
        return jsonify({"success": False, "message": "Registered student profile was not found.", "profile": None}), 404
    return jsonify({"success": True, "profile": student})


@app.route("/api/staff", methods=["GET"])
@login_required
@role_required("admin")
def api_staff_list():
    return jsonify(get_all_staff())


@app.route("/api/logout", methods=["POST"])
@login_required
def api_logout():
    session.pop("user", None)
    session.pop("role", None)
    return jsonify({"success": True, "message": "Logged out."})


# ── API: Dashboard ───────────────────────────────────────────────────────────

@app.route("/api/dashboard/stats")
@login_required
@role_required("admin", "staff", "student")
def api_stats():
    if session.get("role") == "student":
        student_id = get_student_id_for_username(session.get("user"))
        records = get_attendance_today()
        present = any(record.get("student_id") == student_id for record in records)
        return jsonify({
            "total_students": 1 if student_id else 0,
            "present_today": int(present),
            "absent_today": int(bool(student_id) and not present),
            "total_records": 0,
            "departments": 1 if student_id else 0,
        })
    stats = get_summary_stats()
    return jsonify(stats)


# ── API: Attendance ──────────────────────────────────────────────────────────

@app.route("/api/attendance/today")
@login_required
@role_required("admin", "staff", "student")
def api_attendance_today():
    records = get_attendance_today()
    if session.get("role") == "student":
        student_id = get_student_id_for_username(session.get("user"))
        records = [record for record in records if record.get("student_id") == student_id]
    return jsonify(records)


@app.route("/api/attendance/by-date")
@login_required
@role_required("admin", "staff")
def api_attendance_by_date():
    target = request.args.get("date", date.today().isoformat())
    records = get_attendance_by_date(target)
    return jsonify(records)


@app.route("/api/attendance/range")
@login_required
@role_required("admin", "staff")
def api_attendance_range():
    start = request.args.get("start", date.today().isoformat())
    end = request.args.get("end", date.today().isoformat())
    dept = request.args.get("department", "")
    records = get_attendance_range(start, end, dept)
    return jsonify(records)


@app.route("/api/attendance/mark", methods=["POST"])
@login_required
@role_required("admin", "staff")
def api_mark_attendance():
    data = request.get_json(force=True)
    student_id = data.get("student_id", "").strip()
    method = data.get("method", "manual")

    if not student_id:
        return jsonify({"success": False, "message": "Student ID required."}), 400

    student = get_student(student_id)
    if not student:
        return jsonify({"success": False, "message": f"Student '{student_id}' not found."}), 404

    # Determine status based on time
    now = datetime.now().strftime("%H:%M")
    status = "Present" if now <= WORKING_HOURS_START else "Late"

    result = mark_attendance(student_id, method=method, status=status)
    result["student_name"] = student["name"]
    return jsonify(result)


@app.route("/api/attendance/checkout", methods=["POST"])
@login_required
@role_required("admin", "staff")
def api_checkout():
    data = request.get_json(force=True)
    student_id = data.get("student_id", "").strip()
    if not student_id:
        return jsonify({"success": False, "message": "Student ID required."}), 400
    result = mark_checkout(student_id)
    return jsonify(result)


@app.route("/api/attendance/capture", methods=["POST"])
@app.route("/api/attendance/capture-photo", methods=["POST"])
@login_required
@role_required("admin", "staff")
def api_capture_photo():
    """Receive a base64 photo and save it for the attendance record."""
    data = request.get_json(force=True)
    student_id = data.get("student_id", "").strip()
    photo_data = data.get("photo", "")

    if not student_id or not photo_data:
        return jsonify({"success": False, "message": "Student ID and photo required."}), 400

    filename = save_attendance_photo(student_id, photo_data)
    if filename:
        return jsonify({"success": True, "filename": filename,
                        "message": "Photo saved successfully."})
    else:
        return jsonify({"success": False, "message": "Failed to save photo."}), 500


@app.route("/api/attendance/auto", methods=["POST"])
@login_required
@role_required("admin", "staff", "student")
def api_auto_attendance():
    """Recognize a face, mark attendance, save the photo, and verify by voice."""
    data = request.get_json(force=True)
    student_id = data.get("student_id", "").strip()
    photo_data = data.get("photo", "")
    use_voice = bool(data.get("use_voice", True))
    student_account_id = None
    if session.get("role") == "student":
        student_account_id = get_student_id_for_username(session.get("user"))
        if not student_account_id:
            return jsonify({"success": False, "message": "No student profile is linked to this account."}), 400
        if student_id and student_id != student_account_id:
            return jsonify({"success": False, "message": "You can only mark your own attendance."}), 403
    if not photo_data:
        return jsonify({"success": False, "message": "Camera photo is required."}), 400

    if not student_id:
        try:
            import cv2
            import face_recognition
            import numpy as np
            from config import FACE_DETECTION_MODEL, FACE_RECOGNITION_TOLERANCE
            from train_model import load_encodings, model_exists

            if not model_exists():
                return jsonify({"success": False, "message": "Face model is not trained yet."}), 400
            encoded = photo_data.split(",", 1)[-1]
            image = cv2.imdecode(np.frombuffer(base64.b64decode(encoded), np.uint8), cv2.IMREAD_COLOR)
            if image is None:
                return jsonify({"success": False, "message": "Captured image could not be read."}), 400
            rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            locations = face_recognition.face_locations(rgb, model=FACE_DETECTION_MODEL)
            detected = face_recognition.face_encodings(rgb, locations)
            known_data = load_encodings()
            if not detected:
                return jsonify({"success": False, "message": "No face detected. Look at the camera and try again."}), 400
            if len(detected) > 1:
                return jsonify({"success": False, "message": "Multiple faces detected. Only one student may attend at a time."}), 400

            face_encoding = detected[0]
            best_student = None
            best_distance = float("inf")
            for candidate_id, known_encodings in known_data.items():
                distances = face_recognition.face_distance(known_encodings, face_encoding)
                if len(distances) and float(np.min(distances)) < best_distance:
                    best_distance = float(np.min(distances))
                    best_student = candidate_id
            if best_student is None or best_distance > FACE_RECOGNITION_TOLERANCE:
                return jsonify({"success": False, "message": "Face not recognized. Train the model or try again."}), 404
            student_id = best_student
            if student_account_id and student_id != student_account_id:
                return jsonify({"success": False, "message": "The captured face does not match your student account."}), 403
        except Exception as exc:
            return jsonify({"success": False, "message": f"Face recognition failed: {exc}"}), 500

    student = get_student(student_id)
    if not student:
        return jsonify({"success": False, "message": f"Student '{student_id}' not found."}), 404

    now = datetime.now().strftime("%H:%M")
    status = "Present" if now <= WORKING_HOURS_START else "Late"
    attendance_result = mark_attendance(student_id, method="manual+photo", status=status)
    response = {**attendance_result, "student_id": student_id,
                "student_name": student["name"], "voice": None}

    if attendance_result["success"]:
        filename = save_attendance_photo(student_id, photo_data)
        response["photo"] = filename
        if use_voice:
            try:
                from voice_recognition import recognize_voice
                voice = recognize_voice()
                response["voice"] = voice
            except Exception as exc:
                response["voice"] = {"recognized": False, "message": f"Voice check failed: {exc}"}
    return jsonify(response)


# ── API: Photos ──────────────────────────────────────────────────────────────

@app.route("/api/photos/<filename>")
@login_required
@role_required("admin", "staff")
def serve_photo(filename):
    return send_from_directory(PHOTOS_DIR, filename)


# ── API: Students ────────────────────────────────────────────────────────────

@app.route("/api/students")
@login_required
@role_required("admin", "staff")
def api_students():
    query = request.args.get("q", "").strip()
    if query:
        students = search_students(query)
    else:
        students = get_all_students()
    return jsonify(students)


@app.route("/api/students/<student_id>", methods=["GET"])
@login_required
@role_required("admin", "staff")
def api_get_student(student_id):
    student = get_student(student_id)
    if student:
        return jsonify(student)
    return jsonify({"error": "Not found"}), 404


@app.route("/api/students/<student_id>", methods=["DELETE"])
@login_required
@role_required("admin")
def api_delete_student(student_id):
    delete_student(student_id)
    return jsonify({"success": True, "message": f"Student {student_id} deleted."})


@app.route("/api/students/add", methods=["POST"])
@login_required
@role_required("admin")
def api_add_student():
    data = request.get_json(force=True)
    ok = add_student(
        student_id=data.get("student_id", ""),
        name=data.get("name", ""),
        department=data.get("department", ""),
        course=data.get("course", ""),
        year=data.get("year", 1),
        email=data.get("email", ""),
        phone=data.get("phone", ""),
    )
    if ok:
        return jsonify({"success": True, "message": "Student added."})
    return jsonify({"success": False, "message": "Student ID already exists."}), 409


@app.route("/api/students/<student_id>/face-samples", methods=["POST"])
@login_required
@role_required("admin")
def api_face_samples(student_id):
    """Save browser camera frames as training images for a student."""
    student = get_student(student_id)
    if not student:
        return jsonify({"success": False, "message": "Student not found."}), 404

    data = request.get_json(force=True)
    samples = data.get("samples", [])
    if not isinstance(samples, list) or not samples:
        return jsonify({"success": False, "message": "At least one photo is required."}), 400

    dataset_dir = os.path.join(BASE_DIR, "dataset", student_id)
    os.makedirs(dataset_dir, exist_ok=True)
    saved = 0
    for index, encoded in enumerate(samples[:30]):
        try:
            payload = encoded.split(",", 1)[-1]
            image_bytes = base64.b64decode(payload, validate=True)
            filename = f"{student_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{index:03d}.jpg"
            with open(os.path.join(dataset_dir, filename), "wb") as image_file:
                image_file.write(image_bytes)
            saved += 1
        except (ValueError, TypeError):
            continue

    if not saved:
        return jsonify({"success": False, "message": "No valid photos were received."}), 400
    from database import update_student
    total_for_student = len([
        name for name in os.listdir(dataset_dir)
        if name.lower().endswith((".jpg", ".jpeg", ".png"))
    ])
    update_student(student_id, has_face=1 if total_for_student >= 5 else 0)
    return jsonify({"success": True, "saved": saved,
                    "message": f"Saved {saved} face sample(s) for {student_id}."})


@app.route("/api/voice/register", methods=["POST"])
@login_required
@role_required("admin", "staff")
def api_voice_register():
    """Record voice samples using the server microphone for a student."""
    data = request.get_json(force=True)
    student_id = data.get("student_id", "").strip()
    count = min(max(int(data.get("count", 5)), 1), 10)
    if not get_student(student_id):
        return jsonify({"success": False, "message": "Student not found."}), 404
    from voice_register import register_voice
    ok, message = register_voice(student_id, count=count)
    if ok:
        from database import update_student
        update_student(student_id, has_voice=1)
    return jsonify({"success": ok, "message": message}), 200 if ok else 400


@app.route("/api/voice/recognize", methods=["POST"])
@login_required
@role_required("admin", "staff")
def api_voice_recognize():
    """Run the existing server-side voice recognition attendance pipeline."""
    from voice_recognition import mark_by_voice
    return jsonify(mark_by_voice())


@app.route("/api/models/status")
@login_required
@role_required("admin", "staff")
def api_model_status():
    from train_model import model_exists
    from voice_recognition import voice_model_exists
    dataset_dir = os.path.join(BASE_DIR, "dataset")
    sample_counts = {}
    if os.path.isdir(dataset_dir):
        for student_id in os.listdir(dataset_dir):
            student_dir = os.path.join(dataset_dir, student_id)
            if os.path.isdir(student_dir):
                sample_counts[student_id] = len([
                    name for name in os.listdir(student_dir)
                    if name.lower().endswith((".jpg", ".jpeg", ".png"))
                ])
    training_ready = bool(sample_counts) and all(count >= 5 for count in sample_counts.values())
    total_samples = sum(sample_counts.values())
    newest_sample = max(
        (os.path.getmtime(os.path.join(dataset_dir, student_id, filename))
         for student_id in sample_counts
         for filename in os.listdir(os.path.join(dataset_dir, student_id))
         if filename.lower().endswith((".jpg", ".jpeg", ".png"))),
        default=0,
    )
    model_path = os.path.join(BASE_DIR, "model", "face_encodings.pkl")
    model_current = model_exists() and os.path.getmtime(model_path) >= newest_sample
    return jsonify({"face_model": model_exists(), "voice_model": voice_model_exists(),
                    "face_training_ready": training_ready,
                    "face_model_current": model_current,
                    "face_sample_total": total_samples,
                    "face_sample_counts": sample_counts})


@app.route("/api/models/train-face", methods=["POST"])
@login_required
@role_required("admin")
def api_train_face():
    from train_model import train_face_model
    ok, message = train_face_model()
    return jsonify({"success": ok, "message": message}), 200 if ok else 400


@app.route("/api/models/train-voice", methods=["POST"])
@login_required
@role_required("admin")
def api_train_voice():
    from voice_register import train_voice_model
    ok, message = train_voice_model()
    return jsonify({"success": ok, "message": message}), 200 if ok else 400


# ── API: CSV Export ──────────────────────────────────────────────────────────

@app.route("/api/attendance/export/csv")
@login_required
def api_export_csv():
    """Export attendance data as a CSV file for download."""
    target_date = request.args.get("date", "")
    start = request.args.get("start", "")
    end = request.args.get("end", "")

    if start and end:
        records = get_attendance_range(start, end)
    elif target_date:
        records = get_attendance_by_date(target_date)
    else:
        records = get_attendance_today()

    # Build CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Header row
    writer.writerow([
        "Student ID", "Name", "Department", "Date",
        "Time In", "Time Out", "Method", "Status", "Photo"
    ])

    for r in records:
        writer.writerow([
            r.get("student_id", ""),
            r.get("name", ""),
            r.get("department", ""),
            r.get("date", ""),
            r.get("time_in", ""),
            r.get("time_out", ""),
            r.get("method", ""),
            r.get("status", ""),
            r.get("photo_path", ""),
        ])

    output.seek(0)

    # Create a BytesIO for sending
    byte_output = io.BytesIO()
    byte_output.write(output.getvalue().encode("utf-8-sig"))  # BOM for Excel
    byte_output.seek(0)

    filename = f"attendance_{date.today().isoformat()}.csv"

    return send_file(
        byte_output,
        mimetype="text/csv",
        as_attachment=True,
        download_name=filename,
    )


@app.route("/api/reports/<report_type>")
@login_required
@role_required("admin", "staff")
def api_report(report_type):
    """Generate and download one of the existing Excel report types."""
    from report import (generate_daily_report, generate_range_report,
                        generate_student_report)
    try:
        if report_type == "daily":
            filepath = generate_daily_report(request.args.get("date") or date.today().isoformat())
        elif report_type == "range":
            filepath = generate_range_report(
                request.args["start"], request.args["end"], request.args.get("department", ""))
        elif report_type == "student":
            filepath = generate_student_report(request.args["student_id"])
        else:
            return jsonify({"success": False, "message": "Unknown report type."}), 400
    except (KeyError, ValueError) as exc:
        return jsonify({"success": False, "message": f"Invalid report parameters: {exc}"}), 400
    return send_file(filepath, as_attachment=True)


# ── Run ──────────────────────────────────────────────────────────────────────

def start_server(host="0.0.0.0", port=5000, debug=True):
    """Initialize DB and start the Flask dev server."""
    initialize_database()
    print("=" * 50)
    print("  Smart Attendance System — Web Server")
    print(f"  Open http://localhost:{port} in your browser")
    print("=" * 50)
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    start_server()