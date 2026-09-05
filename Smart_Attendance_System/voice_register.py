"""
voice_register.py - Record and save voice samples for a student
"""

import os
import time
import pickle
import numpy as np
import sounddevice as sd
import soundfile as sf
from sklearn.preprocessing import LabelEncoder
from sklearn.svm import SVC
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

try:
    import librosa
    LIBROSA_OK = True
except ImportError:
    LIBROSA_OK = False

from config import (DATASET_DIR, MODEL_DIR, VOICE_MODEL_PATH, LABEL_ENC_PATH,
                    VOICE_SAMPLE_RATE, VOICE_DURATION, VOICE_N_MFCC,
                    VOICE_SAMPLES_COUNT)


def _voice_dir(student_id: str) -> str:
    path = os.path.join(DATASET_DIR, student_id, "voice")
    os.makedirs(path, exist_ok=True)
    return path


def record_sample(duration: int = VOICE_DURATION,
                  sample_rate: int = VOICE_SAMPLE_RATE) -> np.ndarray:
    """Record audio from the microphone and return as numpy array."""
    audio = sd.rec(
        int(duration * sample_rate),
        samplerate=sample_rate,
        channels=1,
        dtype="float32"
    )
    sd.wait()
    return audio.flatten()


def save_voice_sample(student_id: str, audio: np.ndarray,
                      sample_rate: int = VOICE_SAMPLE_RATE,
                      sample_index: int = 0) -> str:
    """Save a voice sample as a WAV file and return the file path."""
    dir_path   = _voice_dir(student_id)
    timestamp  = int(time.time())
    filename   = f"{student_id}_voice_{sample_index:02d}_{timestamp}.wav"
    filepath   = os.path.join(dir_path, filename)
    sf.write(filepath, audio, sample_rate)
    return filepath


def extract_mfcc(filepath: str,
                 n_mfcc: int = VOICE_N_MFCC,
                 sample_rate: int = VOICE_SAMPLE_RATE) -> np.ndarray | None:
    """Extract MFCC features from a WAV file."""
    if not LIBROSA_OK:
        raise ImportError("librosa is required: pip install librosa")
    try:
        y, sr = librosa.load(filepath, sr=sample_rate)
        mfcc  = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=n_mfcc)
        return np.mean(mfcc.T, axis=0)
    except Exception as e:
        print(f"[VOICE] MFCC extraction failed for {filepath}: {e}")
        return None


def register_voice(student_id: str,
                   count: int = VOICE_SAMPLES_COUNT,
                   progress_callback=None) -> tuple[bool, str]:
    """
    Record `count` voice samples for a student and store them.
    progress_callback(current, total, message) called at each step.
    Returns (success, message).
    """
    if not LIBROSA_OK:
        return False, "librosa not installed. Run: pip install librosa"

    collected = []
    for i in range(count):
        if progress_callback:
            progress_callback(i, count, f"Recording sample {i+1}/{count}…")
        print(f"[VOICE] Recording sample {i+1}/{count} for {student_id}…")
        time.sleep(0.5)   # short pause before each recording
        audio    = record_sample()
        filepath = save_voice_sample(student_id, audio, sample_index=i)
        collected.append(filepath)
        print(f"[VOICE] Saved: {filepath}")

    if progress_callback:
        progress_callback(count, count, "Registration complete!")

    return True, f"{len(collected)} voice sample(s) saved for {student_id}."


def train_voice_model(progress_callback=None) -> tuple[bool, str]:
    """
    Build a voice recognition model (SVM) from all recorded voice samples.
    Returns (success, message).
    """
    if not LIBROSA_OK:
        return False, "librosa not installed."

    X, y = [], []
    students = [
        d for d in os.listdir(DATASET_DIR)
        if os.path.isdir(os.path.join(DATASET_DIR, d))
    ] if os.path.isdir(DATASET_DIR) else []

    for sid in students:
        voice_dir = os.path.join(DATASET_DIR, sid, "voice")
        if not os.path.isdir(voice_dir):
            continue
        wav_files = [
            os.path.join(voice_dir, f) for f in os.listdir(voice_dir)
            if f.endswith(".wav")
        ]
        for wf in wav_files:
            feat = extract_mfcc(wf)
            if feat is not None:
                X.append(feat)
                y.append(sid)

    if len(set(y)) < 2:
        return False, "Need voice samples for at least 2 students to train."

    X = np.array(X)
    y = np.array(y)

    le    = LabelEncoder()
    y_enc = le.fit_transform(y)

    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("svm",    SVC(kernel="rbf", C=10, gamma="scale", probability=True))
    ])
    pipeline.fit(X, y_enc)

    os.makedirs(MODEL_DIR, exist_ok=True)
    with open(VOICE_MODEL_PATH, "wb") as f:
        pickle.dump(pipeline, f)
    with open(LABEL_ENC_PATH, "wb") as f:
        pickle.dump(le, f)

    msg = f"Voice model trained with {len(X)} sample(s) from {len(set(y))} student(s)."
    print(f"[VOICE] {msg}")
    return True, msg


if __name__ == "__main__":
    student_id = input("Student ID: ").strip()
    ok, msg    = register_voice(
        student_id,
        progress_callback=lambda c, t, m: print(f"  [{c}/{t}] {m}")
    )
    print(msg)
    if ok:
        ok2, msg2 = train_voice_model()
        print(msg2)
