"""Convenience launcher for the nested Smart Attendance project."""

from pathlib import Path
import runpy


PROJECT_MAIN = Path(__file__).parent / "Smart_Attendance_System" / "main.py"

if __name__ == "__main__":
    runpy.run_path(str(PROJECT_MAIN), run_name="__main__")
