"""
main.py - Entry point for Smart Attendance System
"""

import os
import sys

# Ensure the project root is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import initialize_database

def main():
    """Initialize the database and launch the web server."""
    print("=" * 50)
    print("  Smart Attendance System")
    print("  Face + Voice Recognition")
    print("=" * 50)

    # Bootstrap the database
    initialize_database()

    from app import start_server
    start_server(host="127.0.0.1", port=5000, debug=False)


if __name__ == "__main__":
    main()
