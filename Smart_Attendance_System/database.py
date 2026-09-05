"""
database.py - SQLite database management for Smart Attendance System
"""

import sqlite3
import os
import base64
from datetime import datetime, date
from config import DATABASE_PATH, BASE_DIR


# Directory for storing captured attendance photos
PHOTOS_DIR = os.path.join(BASE_DIR, "photos")
os.makedirs(PHOTOS_DIR, exist_ok=True)


def get_connection():
    """Return a SQLite connection with row_factory for dict-like access."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialize_database():
    """Create all tables if they do not exist."""
    with get_connection() as conn:
        cursor = conn.cursor()

        # Students table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id  TEXT    UNIQUE NOT NULL,
                name        TEXT    NOT NULL,
                department  TEXT    NOT NULL,
                course      TEXT,
                year        INTEGER,
                email       TEXT,
                phone       TEXT,
                photo_dir   TEXT,
                has_face    INTEGER DEFAULT 0,
                has_voice   INTEGER DEFAULT 0,
                created_at  TEXT    DEFAULT (datetime('now','localtime'))
            )
        """)

        # Attendance table (includes photo_path for captured photos)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS attendance (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id    TEXT    NOT NULL,
                date          TEXT    NOT NULL,
                time_in       TEXT,
                time_out      TEXT,
                method        TEXT    DEFAULT 'face',   -- 'face' | 'voice' | 'manual'
                status        TEXT    DEFAULT 'Present', -- 'Present' | 'Late' | 'Absent'
                photo_path    TEXT    DEFAULT NULL,
                marked_at     TEXT    DEFAULT (datetime('now','localtime')),
                FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
                UNIQUE (student_id, date)
            )
        """)

        # Migrate: add photo_path column if missing (for existing databases)
        try:
            cursor.execute("SELECT photo_path FROM attendance LIMIT 1")
        except sqlite3.OperationalError:
            cursor.execute("ALTER TABLE attendance ADD COLUMN photo_path TEXT DEFAULT NULL")
            print("[DB] Migrated: added photo_path column to attendance table.")

        # Users / admin table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                username  TEXT UNIQUE NOT NULL,
                password  TEXT NOT NULL,
                role      TEXT DEFAULT 'admin',
                student_id TEXT UNIQUE
            )
        """)

        try:
            cursor.execute("SELECT student_id FROM users LIMIT 1")
        except sqlite3.OperationalError:
            cursor.execute("ALTER TABLE users ADD COLUMN student_id TEXT")

        # Staff / teacher profile table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS staff (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                username    TEXT UNIQUE NOT NULL,
                staff_id    TEXT UNIQUE NOT NULL,
                name        TEXT NOT NULL,
                department  TEXT NOT NULL,
                email       TEXT,
                phone       TEXT,
                designation TEXT DEFAULT 'Teacher',
                created_at  TEXT DEFAULT (datetime('now','localtime'))
            )
        """)

        # Insert the default accounts if they are not present.
        default_users = [
            ("admin", "admin123", "admin"),
            ("staff", "staff123", "staff"),
            ("student", "student123", "student"),
        ]
        for username, password, role in default_users:
            cursor.execute("SELECT COUNT(*) FROM users WHERE username = ?", (username,))
            if cursor.fetchone()[0] == 0:
                cursor.execute(
                    "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                    (username, password, role)
                )

        # Link the bundled student account to the only registered student when
        # the database has not been configured with an explicit link yet.
        cursor.execute("""
            UPDATE users SET student_id = (
                SELECT student_id FROM students ORDER BY id LIMIT 1
            )
            WHERE username = 'student' AND role = 'student'
              AND student_id IS NULL
              AND (SELECT COUNT(*) FROM students) = 1
        """)

        conn.commit()
    print("[DB] Database initialized successfully.")


# ─────────────────────────── STUDENT CRUD ────────────────────────────────────

def add_student(student_id: str, name: str, department: str,
                course: str = "", year: int = 1,
                email: str = "", phone: str = "") -> bool:
    """Insert a new student. Returns True on success."""
    photo_dir = os.path.join("dataset", student_id)
    try:
        with get_connection() as conn:
            conn.execute("""
                INSERT INTO students
                    (student_id, name, department, course, year, email, phone, photo_dir)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (student_id, name, department, course, year, email, phone, photo_dir))
            conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False


def update_student(student_id: str, **fields) -> bool:
    """Update student fields by student_id."""
    if not fields:
        return False
    allowed = {"name", "department", "course", "year", "email", "phone",
               "has_face", "has_voice"}
    safe_fields = {k: v for k, v in fields.items() if k in allowed}
    if not safe_fields:
        return False
    set_clause = ", ".join(f"{k} = ?" for k in safe_fields)
    values = list(safe_fields.values()) + [student_id]
    with get_connection() as conn:
        conn.execute(f"UPDATE students SET {set_clause} WHERE student_id = ?", values)
        conn.commit()
    return True


def delete_student(student_id: str) -> bool:
    """Delete a student and their attendance records."""
    with get_connection() as conn:
        conn.execute("DELETE FROM students WHERE student_id = ?", (student_id,))
        conn.commit()
    return True


def get_student(student_id: str) -> dict | None:
    """Fetch one student as a dict."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM students WHERE student_id = ?", (student_id,)
        ).fetchone()
    return dict(row) if row else None


def get_student_id_for_username(username: str) -> str | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT student_id FROM users WHERE username = ? AND role = 'student'",
            (username,)
        ).fetchone()
    return row[0] if row and row[0] else None


def link_student_to_username(username: str, student_id: str) -> bool:
    try:
        with get_connection() as conn:
            linked = conn.execute(
                "SELECT username FROM users WHERE student_id = ? AND username != ?",
                (student_id, username)
            ).fetchone()
            if linked:
                return False
            conn.execute(
                "UPDATE users SET student_id = ? WHERE username = ? AND role = 'student'",
                (student_id, username)
            )
            conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False


def get_all_students() -> list[dict]:
    """Return all students as a list of dicts."""
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM students ORDER BY name").fetchall()
    return [dict(r) for r in rows]


def get_student_count() -> int:
    with get_connection() as conn:
        return conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]


def search_students(query: str) -> list[dict]:
    """Search students by name, id, or department."""
    like = f"%{query}%"
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT * FROM students
            WHERE name LIKE ? OR student_id LIKE ? OR department LIKE ?
            ORDER BY name
        """, (like, like, like)).fetchall()
    return [dict(r) for r in rows]


# ─────────────────────────── ATTENDANCE CRUD ─────────────────────────────────

def mark_attendance(student_id: str, method: str = "face",
                    status: str = "Present") -> dict:
    """
    Mark today's attendance for a student.
    First call  → sets time_in  (action='in').
    Explicit checkout via mark_checkout() → sets time_out.
    Automatic face recognition never sets time_out — only the first hit counts.
    Returns {'success': bool, 'message': str, 'action': 'in'|'duplicate'}.
    """
    today  = date.today().isoformat()
    now    = datetime.now().strftime("%H:%M:%S")
    result = {"success": False, "message": "", "action": ""}

    try:
        with get_connection() as conn:
            existing = conn.execute(
                "SELECT * FROM attendance WHERE student_id = ? AND date = ?",
                (student_id, today)
            ).fetchone()

            if existing is None:
                conn.execute("""
                    INSERT INTO attendance (student_id, date, time_in, method, status)
                    VALUES (?, ?, ?, ?, ?)
                """, (student_id, today, now, method, status))
                conn.commit()
                result.update(success=True,
                              message=f"Time-in recorded at {now}",
                              action="in")
            else:
                result.update(success=False,
                              message="Already marked present today.",
                              action="duplicate")
    except sqlite3.IntegrityError:
        result.update(success=False,
                      message="Attendance already recorded (concurrent write).",
                      action="duplicate")
    except Exception as e:
        result.update(success=False, message=f"Database error: {e}", action="error")

    return result


def mark_checkout(student_id: str) -> dict:
    """Explicitly set time_out for today's record. Separate from auto-recognition."""
    today  = date.today().isoformat()
    now    = datetime.now().strftime("%H:%M:%S")
    result = {"success": False, "message": "", "action": ""}

    try:
        with get_connection() as conn:
            existing = conn.execute(
                "SELECT * FROM attendance WHERE student_id = ? AND date = ?",
                (student_id, today)
            ).fetchone()

            if existing is None:
                result.update(success=False,
                              message="No time-in record found for today.",
                              action="error")
            elif existing["time_out"] is not None:
                result.update(success=False,
                              message="Already checked out today.",
                              action="duplicate")
            else:
                conn.execute("""
                    UPDATE attendance SET time_out = ?
                    WHERE student_id = ? AND date = ?
                """, (now, student_id, today))
                conn.commit()
                result.update(success=True,
                              message=f"Time-out recorded at {now}",
                              action="out")
    except Exception as e:
        result.update(success=False, message=f"Database error: {e}", action="error")

    return result


# ─────────────────────────── PHOTO MANAGEMENT ────────────────────────────────

def save_attendance_photo(student_id: str, photo_base64: str,
                          target_date: str = None) -> str | None:
    """
    Save a base64-encoded photo to disk and update the attendance record.
    Returns the saved filename or None on failure.
    """
    if target_date is None:
        target_date = date.today().isoformat()

    try:
        # Decode base64 image data (strip data URI prefix if present)
        if "," in photo_base64:
            photo_base64 = photo_base64.split(",", 1)[1]
        photo_bytes = base64.b64decode(photo_base64)

        # Generate filename: studentID_date_timestamp.jpg
        timestamp = datetime.now().strftime("%H%M%S")
        filename = f"{student_id}_{target_date}_{timestamp}.jpg"
        filepath = os.path.join(PHOTOS_DIR, filename)

        with open(filepath, "wb") as f:
            f.write(photo_bytes)

        # Update the attendance record with the photo path
        with get_connection() as conn:
            conn.execute("""
                UPDATE attendance SET photo_path = ?
                WHERE student_id = ? AND date = ?
            """, (filename, student_id, target_date))
            conn.commit()

        print(f"[DB] Photo saved: {filename}")
        return filename

    except Exception as e:
        print(f"[DB] Error saving photo: {e}")
        return None


def get_attendance_today() -> list[dict]:
    """Return today's attendance records joined with student info."""
    today = date.today().isoformat()
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT a.*, s.name, s.department
            FROM attendance a
            JOIN students s ON a.student_id = s.student_id
            WHERE a.date = ?
            ORDER BY a.marked_at DESC
        """, (today,)).fetchall()
    return [dict(r) for r in rows]


def get_attendance_with_photos() -> list[dict]:
    """Return today's attendance records, including captured photo paths."""
    return get_attendance_today()


def get_attendance_by_date(target_date: str) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT a.*, s.name, s.department
            FROM attendance a
            JOIN students s ON a.student_id = s.student_id
            WHERE a.date = ?
            ORDER BY a.time_in
        """, (target_date,)).fetchall()
    return [dict(r) for r in rows]


def get_attendance_by_student(student_id: str) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT * FROM attendance WHERE student_id = ?
            ORDER BY date DESC
        """, (student_id,)).fetchall()
    return [dict(r) for r in rows]


def get_attendance_range(start_date: str, end_date: str,
                         department: str = "") -> list[dict]:
    with get_connection() as conn:
        if department:
            rows = conn.execute("""
                SELECT a.*, s.name, s.department, s.course
                FROM attendance a
                JOIN students s ON a.student_id = s.student_id
                WHERE a.date BETWEEN ? AND ? AND s.department = ?
                ORDER BY a.date DESC, s.name
            """, (start_date, end_date, department)).fetchall()
        else:
            rows = conn.execute("""
                SELECT a.*, s.name, s.department, s.course
                FROM attendance a
                JOIN students s ON a.student_id = s.student_id
                WHERE a.date BETWEEN ? AND ?
                ORDER BY a.date DESC, s.name
            """, (start_date, end_date)).fetchall()
    return [dict(r) for r in rows]


def get_attendance_count_today() -> int:
    today = date.today().isoformat()
    with get_connection() as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM attendance WHERE date = ?", (today,)
        ).fetchone()[0]


def get_summary_stats() -> dict:
    """Return quick dashboard stats."""
    today = date.today().isoformat()
    with get_connection() as conn:
        total_students  = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
        present_today   = conn.execute(
            "SELECT COUNT(*) FROM attendance WHERE date = ?", (today,)
        ).fetchone()[0]
        total_records   = conn.execute("SELECT COUNT(*) FROM attendance").fetchone()[0]
        departments     = conn.execute(
            "SELECT COUNT(DISTINCT department) FROM students"
        ).fetchone()[0]
    return {
        "total_students": total_students,
        "present_today":  present_today,
        "absent_today":   max(0, total_students - present_today),
        "total_records":  total_records,
        "departments":    departments,
    }


# ─────────────────────────── AUTH ────────────────────────────────────────────

def verify_user(username: str, password: str, role: str | None = None) -> bool:
    """Return whether credentials are valid, optionally requiring a role."""
    with get_connection() as conn:
        query = "SELECT * FROM users WHERE username = ? AND password = ?"
        values = [username, password]
        if role:
            query += " AND role = ?"
            values.append(role)
        row = conn.execute(query, values).fetchone()
    return row is not None


def update_user_password(username: str, password: str) -> bool:
    """Update the password for an existing user account."""
    with get_connection() as conn:
        cursor = conn.execute(
            "UPDATE users SET password = ? WHERE username = ?",
            (password, username),
        )
        conn.commit()
    return cursor.rowcount == 1


def save_staff_profile(username: str, staff_id: str, name: str, department: str,
                      email: str = "", phone: str = "", designation: str = "Teacher") -> bool:
    """Create or update a teacher/staff profile for a logged in user."""
    username = (username or "").strip()
    if not username or not staff_id or not name or not department:
        return False
    try:
        with get_connection() as conn:
            existing = conn.execute(
                "SELECT id FROM staff WHERE username = ? OR staff_id = ?",
                (username, staff_id)
            ).fetchone()
            if existing:
                conn.execute("""
                    UPDATE staff
                    SET staff_id = ?, name = ?, department = ?, email = ?, phone = ?, designation = ?
                    WHERE username = ? OR staff_id = ?
                """, (staff_id, name, department, email, phone, designation, username, staff_id))
            else:
                conn.execute("""
                    INSERT INTO staff (username, staff_id, name, department, email, phone, designation)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (username, staff_id, name, department, email, phone, designation))
            conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False


def get_staff_profile_by_username(username: str) -> dict | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM staff WHERE username = ?", (username,)).fetchone()
    return dict(row) if row else None


def get_all_staff() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM staff ORDER BY name").fetchall()
    return [dict(r) for r in rows]


# ─────────────────────────── BOOTSTRAP ───────────────────────────────────────
if __name__ == "__main__":
    initialize_database()
    print("[DB] Ready.")
