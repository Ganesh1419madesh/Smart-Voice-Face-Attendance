# Smart Attendance System

A web attendance management application with a Flask API and a responsive browser dashboard. The existing **face recognition**, **voice recognition**, and SQLite logic remain available to the backend.

---

## Features

| Feature | Description |
|---|---|
| 🎓 Student Registration | Add student info + capture 30 face images |
| 📷 Face Attendance | Real-time webcam face recognition |
| 🎤 Voice Attendance | Record voice → identify speaker → mark attendance |
| 📊 Reports | Daily / date-range / per-student Excel exports |
| 👥 Student Management | Search, view, and delete students |
| ⚙️ Model Training | One-click face model rebuild |
| 🔐 Login | Admin login with SQLite-backed auth |

---

## Project Structure

```
Smart_Attendance_System/
│
├── main.py               # Flask server entry point
├── app.py                # Flask API and static frontend server
├── config.py             # All paths, colours, and settings
├── database.py           # SQLite CRUD (students + attendance)
├── train_model.py        # Collect & save face encodings
├── attendance.py         # Face-recognition attendance CLI helper
├── voice_register.py     # Record voice samples + train SVM model
├── voice_recognition.py  # Predict speaker + mark attendance
├── report.py             # Excel report generation (openpyxl)
├── frontend/
│   ├── index.html            # Web login page
│   ├── dashboard.html        # Dashboard SPA
│   ├── css/style.css         # Responsive design system
│   └── js/app.js             # API, camera, and UI logic
│
├── database/
│   └── attendance.db         # SQLite database (auto-created)
│
├── dataset/
│   └── StudentXXX/           # Face images per student
│       └── voice/            # WAV samples per student
│
├── model/
│   ├── face_encodings.pkl    # Trained face encodings
│   ├── voice_model.pkl       # Trained SVM voice classifier
│   └── label_encoder.pkl     # Voice label encoder
│
├── reports/
│   └── *.xlsx                # Generated Excel reports
│
├── images/
│   └── logo.png              # App logo (optional)
│
├── photos/               # Captured attendance photos
├── requirements.txt
└── README.md
```

---

## Installation

### 1. Install Python 3.10+

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

> **Note:** `dlib` (required by `face-recognition`) needs CMake and a C++ compiler.
> - **Windows:** Install Visual Studio Build Tools, then `pip install cmake dlib`
> - **Ubuntu/Debian:** `sudo apt install cmake libboost-all-dev`
> - **macOS:** `brew install cmake boost`

### 3. Run

```bash
cd Smart_Attendance_System
python main.py
```

Open `http://localhost:5000` after startup. Default login: **admin / admin123**

---

## Usage Workflow

### Register a Student
1. Go to **Register Student**
2. Fill in the form and click **Save Student & Start Capture**
3. Look at the webcam — 30 face images are auto-captured
4. Optionally click **Register Voice** to record voice samples

### Train the Model
1. Go to **Train Model**
2. Click **Train Model Now**
3. Wait for completion (runs in background)

### Mark Attendance
- **Photo-assisted manual:** Open **Take attendance**, start the browser camera, capture a frame, enter a Student ID, and mark them in.
- **Voice / face backend:** The existing Python recognition modules remain available for backend or future API integration.

### Generate Reports
1. Go to **Reports**
2. Choose report type (Daily / Range / Student)
3. Click **Preview** to see data in the table
4. Click **Export to Excel** to save an `.xlsx` file

---

## Configuration

Edit `config.py` to change:

| Setting | Description |
|---|---|
| `FACE_RECOGNITION_TOLERANCE` | Stricter match → lower value (default 0.50) |
| `VOICE_SAMPLES_COUNT` | Voice samples to record per student (default 5) |
| `ATTENDANCE_COOLDOWN_SECONDS` | Prevent duplicate marks (default 30s) |
| `WORKING_HOURS_START` | Time after which attendance is "Late" |
| `ADMIN_USERNAME / ADMIN_PASSWORD` | Default login credentials |
| `CAMERA_INDEX` | Camera device index (0 = default webcam) |

---

## Technology Stack

- **Frontend:** HTML, CSS, and JavaScript
- **Backend:** Flask REST API
- **Face Recognition:** `face_recognition` (dlib-based)
- **Voice Recognition:** `librosa` + `scikit-learn` SVM
- **Audio I/O:** `sounddevice` + `soundfile`
- **Database:** SQLite3 (built-in)
- **Excel Reports:** `openpyxl`
- **Image Processing:** OpenCV + Pillow

---

## Troubleshooting

| Problem | Solution |
|---|---|
| Camera not opening | Check `CAMERA_INDEX` in `config.py` |
| `dlib` install fails | Install CMake + C++ compiler first |
| "No model trained" warning | Go to Train Model and run training |
| Voice not recognized | Re-register voice with more samples |
| Low face recognition accuracy | Lower `FACE_RECOGNITION_TOLERANCE` or add more training images |
