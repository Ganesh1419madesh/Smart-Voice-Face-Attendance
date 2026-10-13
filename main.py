"""Launch the Smart Attendance web frontend and backend together."""

import sys
import threading
import webbrowser
from pathlib import Path
import os


PROJECT_DIR = Path(__file__).parent / "Smart_Attendance_System"
USE_HTTPS = bool(os.environ.get("ATTENDANCE_TLS_CERT") and os.environ.get("ATTENDANCE_TLS_KEY"))
SERVER_URL = f"{'https' if USE_HTTPS else 'http'}://127.0.0.1:5000"

if __name__ == "__main__":
    venv_python = Path(__file__).parent / "venv" / "Scripts" / "python.exe"
    if venv_python.exists() and sys.prefix == sys.base_prefix:
        os.execv(str(venv_python), [str(venv_python), __file__, *sys.argv[1:]])

    sys.path.insert(0, str(PROJECT_DIR))
    from app import start_server

    threading.Timer(1.2, lambda: webbrowser.open(SERVER_URL)).start()
    start_server(host="127.0.0.1", port=5000, debug=False)
