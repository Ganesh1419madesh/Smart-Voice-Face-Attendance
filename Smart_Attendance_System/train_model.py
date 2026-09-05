"""
train_model.py - Train face recognition model using face_recognition library
"""

import os
import pickle
import cv2
import numpy as np
import face_recognition
from config import (DATASET_DIR, MODEL_DIR, FACE_DETECTION_MODEL,
                    MIN_TRAINING_IMAGES)


ENCODINGS_PATH = os.path.join(MODEL_DIR, "face_encodings.pkl")


def collect_encodings(progress_callback=None) -> dict:
    """
    Walk dataset directory and compute face encodings for every student.
    Returns: {'student_id': [encoding, ...], ...}
    """
    data = {}
    students = sorted(os.listdir(DATASET_DIR)) if os.path.isdir(DATASET_DIR) else []

    for idx, student_id in enumerate(students):
        student_path = os.path.join(DATASET_DIR, student_id)
        if not os.path.isdir(student_path):
            continue

        encodings = []
        images = sorted(
            f for f in os.listdir(student_path)
            if f.lower().endswith((".jpg", ".jpeg", ".png"))
        )

        for img_file in images:
            if len(encodings) >= MIN_TRAINING_IMAGES:
                break
            img_path = os.path.join(student_path, img_file)
            try:
                image = face_recognition.load_image_file(img_path)
                locations = face_recognition.face_locations(
                    image, number_of_times_to_upsample=0,
                    model=FACE_DETECTION_MODEL
                )
                found = face_recognition.face_encodings(
                    image, known_face_locations=locations
                )
                if not found:
                    # Browser captures can be dark or small; brighten and enlarge once
                    # before treating the sample as unusable.
                    enhanced = cv2.convertScaleAbs(image, alpha=1.35, beta=35)
                    enhanced = cv2.resize(enhanced, None, fx=1.5, fy=1.5,
                                          interpolation=cv2.INTER_CUBIC)
                    locations = face_recognition.face_locations(
                        enhanced, number_of_times_to_upsample=1,
                        model=FACE_DETECTION_MODEL
                    )
                    found = face_recognition.face_encodings(
                        enhanced, known_face_locations=locations
                    )
                if found:
                    encodings.append(found[0])
            except Exception as e:
                print(f"[TRAIN] Skip {img_path}: {e}")

        if len(encodings) >= MIN_TRAINING_IMAGES:
            data[student_id] = encodings
            print(f"[TRAIN] {student_id}: {len(encodings)} encodings")
        else:
            print(f"[TRAIN] {student_id}: only {len(encodings)} images — need {MIN_TRAINING_IMAGES}")

        if progress_callback:
            progress_callback(idx + 1, len(students), student_id)

    return data


def train_face_model(progress_callback=None) -> tuple[bool, str]:
    """
    Train (save) the face encodings model.
    Returns (success: bool, message: str)
    """
    if not os.path.isdir(DATASET_DIR) or not os.listdir(DATASET_DIR):
        return False, "Dataset directory is empty. Register students first."

    try:
        data = collect_encodings(progress_callback)
        if not data:
            return False, (
                "No detectable faces were found in the captured images. "
                "Recapture the samples with the face closer, brighter, and centered."
            )

        os.makedirs(MODEL_DIR, exist_ok=True)
        with open(ENCODINGS_PATH, "wb") as f:
            pickle.dump(data, f)

        msg = f"Model trained for {len(data)} student(s)."
        print(f"[TRAIN] {msg}")
        return True, msg

    except Exception as e:
        return False, f"Training failed: {e}"


def load_encodings() -> dict:
    """Load pre-trained face encodings from disk."""
    if not os.path.exists(ENCODINGS_PATH):
        return {}
    try:
        with open(ENCODINGS_PATH, "rb") as f:
            return pickle.load(f)
    except Exception as e:
        print(f"[TRAIN] Could not load encodings: {e}")
        return {}


def model_exists() -> bool:
    return os.path.exists(ENCODINGS_PATH)


def get_trained_students() -> list[str]:
    """Return list of student IDs present in the trained model."""
    data = load_encodings()
    return list(data.keys())


if __name__ == "__main__":
    ok, msg = train_face_model(
        progress_callback=lambda i, n, sid: print(f"  [{i}/{n}] {sid}")
    )
    print(msg)
