"""
voice_recognition.py - Real-time voice-based attendance recognition
"""

import os
import pickle
import numpy as np
import sounddevice as sd

try:
    import librosa
    LIBROSA_OK = True
except ImportError:
    LIBROSA_OK = False

from config import (VOICE_MODEL_PATH, LABEL_ENC_PATH,
                    VOICE_SAMPLE_RATE, VOICE_DURATION, VOICE_N_MFCC,
                    WORKING_HOURS_START)
from database import mark_attendance, get_student


CONFIDENCE_THRESHOLD = 0.70   # minimum probability to accept a voice match


def _load_voice_model():
    """Load SVM pipeline and label encoder. Returns (model, le) or (None, None)."""
    if not os.path.exists(VOICE_MODEL_PATH) or not os.path.exists(LABEL_ENC_PATH):
        return None, None
    try:
        with open(VOICE_MODEL_PATH, "rb") as f:
            model = pickle.load(f)
        with open(LABEL_ENC_PATH, "rb") as f:
            le = pickle.load(f)
        return model, le
    except Exception as e:
        print(f"[VREC] Could not load voice model: {e}")
        return None, None


def voice_model_exists() -> bool:
    return os.path.exists(VOICE_MODEL_PATH) and os.path.exists(LABEL_ENC_PATH)


def record_voice(duration: int = VOICE_DURATION,
                 sample_rate: int = VOICE_SAMPLE_RATE) -> np.ndarray:
    """Record audio from the microphone and return as a float32 array."""
    print(f"[VREC] Recording for {duration}s…")
    audio = sd.rec(
        int(duration * sample_rate),
        samplerate=sample_rate,
        channels=1,
        dtype="float32"
    )
    sd.wait()
    print("[VREC] Recording done.")
    return audio.flatten()


def extract_features(audio: np.ndarray,
                     sample_rate: int = VOICE_SAMPLE_RATE,
                     n_mfcc: int = VOICE_N_MFCC) -> np.ndarray | None:
    """Extract MFCC feature vector from a raw audio array."""
    if not LIBROSA_OK:
        raise ImportError("librosa is required: pip install librosa")
    try:
        mfcc = librosa.feature.mfcc(y=audio, sr=sample_rate, n_mfcc=n_mfcc)
        return np.mean(mfcc.T, axis=0)
    except Exception as e:
        print(f"[VREC] Feature extraction failed: {e}")
        return None


def recognize_voice(audio: np.ndarray | None = None) -> dict:
    """
    Record (if audio is None) or use the given audio, then predict the speaker.
    Returns:
        {
            'recognized': bool,
            'student_id': str | None,
            'name': str | None,
            'confidence': float,
            'message': str,
        }
    """
    result = {
        "recognized": False,
        "student_id": None,
        "name": None,
        "confidence": 0.0,
        "message": "",
    }

    if not LIBROSA_OK:
        result["message"] = "librosa not installed."
        return result

    if not voice_model_exists():
        result["message"] = "Voice model not trained yet."
        return result

    model, le = _load_voice_model()
    if model is None:
        result["message"] = "Failed to load voice model."
        return result

    if audio is None:
        audio = record_voice()

    features = extract_features(audio)
    if features is None:
        result["message"] = "Could not extract voice features."
        return result

    features_2d = features.reshape(1, -1)
    proba        = model.predict_proba(features_2d)[0]
    class_idx    = int(np.argmax(proba))
    confidence   = float(proba[class_idx])
    student_id   = le.inverse_transform([class_idx])[0]

    result["confidence"] = confidence

    if confidence < CONFIDENCE_THRESHOLD:
        result["message"] = (
            f"Voice not recognized (confidence {confidence:.0%} < "
            f"{CONFIDENCE_THRESHOLD:.0%} threshold)."
        )
        return result

    info = get_student(student_id)
    name = info["name"] if info else student_id

    result.update(recognized=True, student_id=student_id, name=name,
                  message=f"Recognized: {name} ({confidence:.0%} confidence)")
    return result


def mark_by_voice(on_result=None) -> dict:
    """
    Full pipeline: record → recognize → mark attendance.
    on_result(result_dict) is called with the final outcome dict.
    Returns the outcome dict.
    """
    from datetime import datetime

    recog = recognize_voice()
    outcome = {**recog, "attendance": None}

    if recog["recognized"]:
        from config import WORKING_HOURS_START
        now    = datetime.now().strftime("%H:%M")
        status = "Present" if now <= WORKING_HOURS_START else "Late"
        att    = mark_attendance(recog["student_id"], method="voice", status=status)
        outcome["attendance"] = att
        outcome["message"]    = f"{recog['name']}: {att['message']}"

    if on_result:
        on_result(outcome)

    return outcome


# ── CLI demo ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    while True:
        input("\nPress Enter to start voice recognition (Ctrl+C to exit)…")
        result = mark_by_voice(
            on_result=lambda r: print(
                f"  Student : {r.get('name') or 'Unknown'}\n"
                f"  Conf    : {r['confidence']:.0%}\n"
                f"  Message : {r['message']}"
            )
        )
