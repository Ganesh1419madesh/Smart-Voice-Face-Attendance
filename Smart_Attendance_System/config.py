"""
config.py - Configuration settings for Smart Attendance System
"""

import os

# Base directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Directory paths
DATABASE_DIR = os.path.join(BASE_DIR, "database")
DATASET_DIR  = os.path.join(BASE_DIR, "dataset")
MODEL_DIR    = os.path.join(BASE_DIR, "model")
REPORTS_DIR  = os.path.join(BASE_DIR, "reports")
IMAGES_DIR   = os.path.join(BASE_DIR, "images")
GUI_DIR      = os.path.join(BASE_DIR, "gui")

# File paths
DATABASE_PATH     = os.path.join(DATABASE_DIR, "attendance.db")
VOICE_MODEL_PATH  = os.path.join(MODEL_DIR, "voice_model.pkl")
LABEL_ENC_PATH    = os.path.join(MODEL_DIR, "label_encoder.pkl")
REPORT_PATH       = os.path.join(REPORTS_DIR, "attendance.xlsx")
LOGO_PATH         = os.path.join(IMAGES_DIR, "logo.png")

# Face recognition settings
FACE_RECOGNITION_TOLERANCE = 0.50   # Lower = stricter match
FACE_DETECTION_MODEL       = "hog"  # 'hog' (CPU) or 'cnn' (GPU)
FACE_ENCODINGS_PER_IMAGE   = 1
MIN_TRAINING_IMAGES        = 5

# Camera settings
CAMERA_INDEX     = 0
CAMERA_WIDTH     = 640
CAMERA_HEIGHT    = 480
FRAME_SKIP       = 2   # Process every Nth frame for performance

# Voice recognition settings
VOICE_SAMPLE_RATE    = 22050
VOICE_DURATION       = 3      # seconds to record
VOICE_N_MFCC         = 40     # number of MFCC features
VOICE_N_MELS         = 128
VOICE_SAMPLES_COUNT  = 5      # samples per student during registration

# Attendance settings
ATTENDANCE_COOLDOWN_SECONDS = 30   # prevent duplicate marks within N seconds
WORKING_HOURS_START         = "08:00"
WORKING_HOURS_END           = "18:00"

# GUI settings
APP_TITLE        = "Smart Attendance System"
APP_GEOMETRY     = "1100x680"
PRIMARY_COLOR    = "#1a237e"   # dark indigo
SECONDARY_COLOR  = "#283593"
ACCENT_COLOR     = "#ff6f00"   # amber
BG_COLOR         = "#f5f5f5"
CARD_COLOR       = "#ffffff"
TEXT_COLOR       = "#212121"
MUTED_COLOR      = "#757575"
SUCCESS_COLOR    = "#2e7d32"
ERROR_COLOR      = "#c62828"
WARNING_COLOR    = "#e65100"
FONT_FAMILY      = "Helvetica"

# Login credentials (change in production)
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

# Ensure directories exist
for _dir in [DATABASE_DIR, DATASET_DIR, MODEL_DIR, REPORTS_DIR, IMAGES_DIR, GUI_DIR]:
    os.makedirs(_dir, exist_ok=True)
