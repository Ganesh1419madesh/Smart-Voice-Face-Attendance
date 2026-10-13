"""
train_model.py - Train face recognition model using face_recognition library
"""

import os
import pickle
import numpy as np
import face_recognition
from config import (DATASET_DIR, MODEL_DIR, FACE_DETECTION_MODEL,
                    MIN_TRAINING_IMAGES)


ENCODINGS_PATH = os.path.join(MODEL_DIR, "face_encodings.pkl")
_ENCODINGS_CACHE = None
_ENCODINGS_MTIME = None
TRAINING_MAX_DIMENSION = 640
MAX_TRAINING_IMAGES_PER_STUDENT = 60

try:
    import cv2
except ImportError as exc:
    cv2 = None
    _CV2_IMPORT_ERROR = exc
else:
    _CV2_IMPORT_ERROR = None


def prepare_face_image(image, max_dimension=800):
    """Resize and improve contrast before the expensive face-recognition step."""
    if cv2 is None:
        raise RuntimeError(
            "OpenCV is not installed. Run: python -m pip install opencv-python"
        ) from _CV2_IMPORT_ERROR
    height, width = image.shape[:2]
    largest_dimension = max(height, width)
    if largest_dimension > max_dimension:
        scale = max_dimension / largest_dimension
        image = cv2.resize(image, None, fx=scale, fy=scale,
                           interpolation=cv2.INTER_AREA)

    lab = cv2.cvtColor(image, cv2.COLOR_RGB2LAB)
    lightness, chroma_a, chroma_b = cv2.split(lab)
    lightness = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(lightness)
    return cv2.cvtColor(cv2.merge((lightness, chroma_a, chroma_b)), cv2.COLOR_LAB2RGB)


def _select_training_images(image_paths, max_images=MAX_TRAINING_IMAGES_PER_STUDENT):
    ordered_paths = sorted(image_paths, key=os.path.getmtime)
    if len(ordered_paths) <= max_images:
        return ordered_paths

    interval = (len(ordered_paths) - 1) / (max_images - 1)
    return [ordered_paths[round(index * interval)] for index in range(max_images)]


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
        image_paths = [
            os.path.join(student_path, filename) for filename in os.listdir(student_path)
            if filename.lower().endswith((".jpg", ".jpeg", ".png"))
        ]
        images = _select_training_images(image_paths)

        encodings = []
        for img_path in images:
            try:
                source_image = face_recognition.load_image_file(img_path)
                image = prepare_face_image(source_image, TRAINING_MAX_DIMENSION)
                locations = face_recognition.face_locations(
                    image, number_of_times_to_upsample=0,
                    model=FACE_DETECTION_MODEL
                )
                found = face_recognition.face_encodings(
                    image, known_face_locations=locations
                )
                if not found:
                    # One small retry handles difficult lighting without the slow
                    # upsampled detector used by the old training path.
                    fallback = cv2.convertScaleAbs(image, alpha=1.15, beta=15)
                    locations = face_recognition.face_locations(
                        fallback, number_of_times_to_upsample=0,
                        model=FACE_DETECTION_MODEL
                    )
                    found = face_recognition.face_encodings(fallback,
                                                            known_face_locations=locations)
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
        global _ENCODINGS_CACHE, _ENCODINGS_MTIME
        _ENCODINGS_CACHE = data
        _ENCODINGS_MTIME = os.path.getmtime(ENCODINGS_PATH)

        msg = f"Model trained for {len(data)} student(s)."
        print(f"[TRAIN] {msg}")
        return True, msg

    except Exception as e:
        return False, f"Training failed: {e}"


def load_encodings() -> dict:
    """Load pre-trained face encodings from disk."""
    global _ENCODINGS_CACHE, _ENCODINGS_MTIME
    if not os.path.exists(ENCODINGS_PATH):
        return {}
    try:
        modified_time = os.path.getmtime(ENCODINGS_PATH)
        if _ENCODINGS_CACHE is not None and _ENCODINGS_MTIME == modified_time:
            return _ENCODINGS_CACHE
        with open(ENCODINGS_PATH, "rb") as f:
            _ENCODINGS_CACHE = pickle.load(f)
        _ENCODINGS_MTIME = modified_time
        return _ENCODINGS_CACHE
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
