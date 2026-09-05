"""
attendance.py - Real-time face-recognition attendance marking
"""

import cv2
import face_recognition
import numpy as np
from datetime import datetime

from config import (FACE_RECOGNITION_TOLERANCE, FACE_DETECTION_MODEL,
                    CAMERA_INDEX, CAMERA_WIDTH, CAMERA_HEIGHT, FRAME_SKIP,
                    WORKING_HOURS_START, WORKING_HOURS_END)
from database import mark_attendance, get_student
from train_model import load_encodings, model_exists


def _determine_status() -> str:
    """Return 'Present' or 'Late' based on current time vs working hours."""
    now  = datetime.now().strftime("%H:%M")
    return "Present" if now <= WORKING_HOURS_START else "Late"


class FaceAttendance:
    """
    Manages a live camera session for face-based attendance.
    Usage:
        fa = FaceAttendance(on_recognized=my_callback)
        fa.start()          # blocking — press Q to quit
        fa.stop()
    """

    def __init__(self, on_recognized=None, window_title="Attendance — Press Q to quit"):
        self.on_recognized  = on_recognized   # callable(student_id, name, result_dict)
        self.window_title   = window_title
        self._running       = False
        self._cap           = None
        self._known_data    = {}   # {student_id: [encodings]}
        self._recent_marks  = {}  # {student_id: last_mark_time}
        self._cooldown_sec  = 30
        self._frame_count   = 0

    def load_model(self) -> tuple[bool, str]:
        if not model_exists():
            return False, "Face model not trained yet. Train it first."
        self._known_data = load_encodings()
        if not self._known_data:
            return False, "No encodings in model."
        return True, f"Loaded {len(self._known_data)} student(s)."

    def _recently_marked(self, student_id: str) -> bool:
        last = self._recent_marks.get(student_id)
        if last is None:
            return False
        return (datetime.now() - last).total_seconds() < self._cooldown_sec

    def _recognize_frame(self, frame):
        """
        Detect and recognize faces in a BGR frame.
        Returns list of (top, right, bottom, left, student_id, name, color).
        """
        small  = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
        rgb    = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)

        locations = face_recognition.face_locations(rgb, model=FACE_DETECTION_MODEL)
        encodings = face_recognition.face_encodings(rgb, locations)

        results = []
        for enc, loc in zip(encodings, locations):
            top, right, bottom, left = [v * 2 for v in loc]
            label      = "Unknown"
            student_id = None
            color      = (0, 0, 200)  # red for unknown

            for sid, known_encs in self._known_data.items():
                matches   = face_recognition.compare_faces(
                    known_encs, enc, tolerance=FACE_RECOGNITION_TOLERANCE
                )
                distances = face_recognition.face_distance(known_encs, enc)

                if any(matches):
                    best_idx   = int(np.argmin(distances))
                    if matches[best_idx]:
                        student_id = sid
                        info = get_student(sid)
                        label = info["name"] if info else sid
                        color = (0, 200, 0)  # green
                        break

            results.append((top, right, bottom, left, student_id, label, color))
        return results

    def _annotate_frame(self, frame, detections):
        for (top, right, bottom, left, sid, label, color) in detections:
            cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
            cv2.rectangle(frame, (left, bottom - 28), (right, bottom), color, cv2.FILLED)
            cv2.putText(frame, label, (left + 6, bottom - 8),
                        cv2.FONT_HERSHEY_DUPLEX, 0.65, (255, 255, 255), 1)
        # Overlay clock
        ts = datetime.now().strftime("%Y-%m-%d  %H:%M:%S")
        cv2.putText(frame, ts, (10, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (200, 200, 200), 1)
        return frame

    def start(self):
        """Open camera and run recognition loop (blocking)."""
        ok, msg = self.load_model()
        if not ok:
            print(f"[ATT] {msg}")
            return

        self._cap = cv2.VideoCapture(CAMERA_INDEX)
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH,  CAMERA_WIDTH)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
        self._running = True
        print("[ATT] Camera started. Press Q to quit.")

        while self._running:
            ret, frame = self._cap.read()
            if not ret:
                print("[ATT] Camera read failed.")
                break

            self._frame_count += 1
            detections = []

            if self._frame_count % FRAME_SKIP == 0:
                detections = self._recognize_frame(frame)

                for (_, _, _, _, sid, label, _) in detections:
                    if sid and not self._recently_marked(sid):
                        status = _determine_status()
                        result = mark_attendance(sid, method="face", status=status)
                        self._recent_marks[sid] = datetime.now()
                        if self.on_recognized:
                            self.on_recognized(sid, label, result)

            self._annotate_frame(frame, detections)
            cv2.imshow(self.window_title, frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

        self.stop()

    def stop(self):
        self._running = False
        if self._cap:
            self._cap.release()
        cv2.destroyAllWindows()
        print("[ATT] Camera stopped.")


# ── Standalone run ────────────────────────────────────────────────────────────
def run_attendance_cli():
    def on_recognized(sid, name, result):
        icon = "✓" if result["success"] else "!"
        print(f"[{icon}] {name} ({sid}): {result['message']}")

    fa = FaceAttendance(on_recognized=on_recognized)
    fa.start()


if __name__ == "__main__":
    run_attendance_cli()
