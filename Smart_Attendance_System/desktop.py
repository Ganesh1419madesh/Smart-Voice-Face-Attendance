import threading
import time
import webview

from app import app
from database import initialize_database

def start_flask():
    initialize_database()
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False,
        use_reloader=False
    )

if __name__ == "__main__":
    flask_thread = threading.Thread(target=start_flask, daemon=True)
    flask_thread.start()

    time.sleep(2)

    webview.create_window(
        "Smart Attendance System",
        "http://127.0.0.1:5000",
        width=1280,
        height=800,
        min_size=(1000, 650),
        resizable=True
    )

    webview.start()