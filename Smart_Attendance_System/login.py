"""
login.py - Login window for Smart Attendance System
"""

import tkinter as tk
from tkinter import ttk, messagebox
import os

from config import (APP_TITLE, PRIMARY_COLOR, SECONDARY_COLOR, ACCENT_COLOR,
                    BG_COLOR, CARD_COLOR, TEXT_COLOR, MUTED_COLOR,
                    ERROR_COLOR, FONT_FAMILY, LOGO_PATH)
from database import verify_user, initialize_database


class LoginWindow:
    def __init__(self):
        initialize_database()

        self.root = tk.Tk()
        self.root.title(f"{APP_TITLE} — Login")
        self.root.resizable(False, False)
        self.root.configure(bg=PRIMARY_COLOR)

        # Centre window
        w, h = 420, 520
        sw   = self.root.winfo_screenwidth()
        sh   = self.root.winfo_screenheight()
        self.root.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

        self._authenticated = False
        self._build_ui()
        self.root.mainloop()

    # ── UI ────────────────────────────────────────────────────────────────────
    def _build_ui(self):
        # Background gradient simulation via two frames
        top = tk.Frame(self.root, bg=PRIMARY_COLOR, height=180)
        top.pack(fill="x")

        # Logo / icon
        logo_lbl = tk.Label(top, bg=PRIMARY_COLOR)
        logo_lbl.pack(pady=(30, 5))
        try:
            from PIL import Image, ImageTk
            img = Image.open(LOGO_PATH).resize((80, 80))
            self._logo_img = ImageTk.PhotoImage(img)
            logo_lbl.config(image=self._logo_img)
        except Exception:
            logo_lbl.config(text="🎓", font=(FONT_FAMILY, 48), fg="white")

        tk.Label(top, text=APP_TITLE, bg=PRIMARY_COLOR,
                 fg="white", font=(FONT_FAMILY, 16, "bold")).pack()
        tk.Label(top, text="Smart Face & Voice Attendance", bg=PRIMARY_COLOR,
                 fg="#9FA8DA", font=(FONT_FAMILY, 9)).pack(pady=(2, 0))

        # Card
        card = tk.Frame(self.root, bg=CARD_COLOR, padx=36, pady=36)
        card.pack(fill="both", expand=True, padx=24, pady=20)

        tk.Label(card, text="Sign In", bg=CARD_COLOR, fg=PRIMARY_COLOR,
                 font=(FONT_FAMILY, 15, "bold")).pack(anchor="w")
        tk.Label(card, text="Enter your credentials to continue",
                 bg=CARD_COLOR, fg=MUTED_COLOR,
                 font=(FONT_FAMILY, 9)).pack(anchor="w", pady=(2, 18))

        # Username
        self._field(card, "Username", "username")
        # Password
        self._field(card, "Password", "password", show="•")

        # Error label
        self.err_var = tk.StringVar()
        tk.Label(card, textvariable=self.err_var, bg=CARD_COLOR,
                 fg=ERROR_COLOR, font=(FONT_FAMILY, 9)).pack(pady=(4, 0))

        # Login button
        btn = tk.Button(card, text="Login", bg=ACCENT_COLOR, fg="white",
                        font=(FONT_FAMILY, 11, "bold"), relief="flat",
                        cursor="hand2", padx=10, pady=10,
                        command=self._on_login)
        btn.pack(fill="x", pady=(14, 0))
        btn.bind("<Enter>", lambda e: btn.config(bg="#E65100"))
        btn.bind("<Leave>", lambda e: btn.config(bg=ACCENT_COLOR))

        # Default creds hint
        tk.Label(card, text="Default: admin / admin123", bg=CARD_COLOR,
                 fg=MUTED_COLOR, font=(FONT_FAMILY, 8, "italic")).pack(pady=(10, 0))

        # Bind Enter key
        self.root.bind("<Return>", lambda e: self._on_login())

    def _field(self, parent, label: str, attr: str, show: str = ""):
        tk.Label(parent, text=label, bg=CARD_COLOR, fg=TEXT_COLOR,
                 font=(FONT_FAMILY, 10, "bold")).pack(anchor="w", pady=(8, 2))
        entry = tk.Entry(parent, show=show, font=(FONT_FAMILY, 11),
                         relief="solid", bd=1, fg=TEXT_COLOR,
                         highlightthickness=2,
                         highlightbackground="#E0E0E0",
                         highlightcolor=PRIMARY_COLOR)
        entry.pack(fill="x", ipady=7)
        setattr(self, f"_{attr}_entry", entry)

    # ── Logic ─────────────────────────────────────────────────────────────────
    def _on_login(self):
        username = self._username_entry.get().strip()
        password = self._password_entry.get().strip()

        if not username or not password:
            self.err_var.set("Please enter both username and password.")
            return

        if verify_user(username, password):
            self._authenticated = True
            self.root.destroy()
            self._launch_dashboard()
        else:
            self.err_var.set("Invalid username or password.")
            self._password_entry.delete(0, "end")
            self._password_entry.focus()

    def _launch_dashboard(self):
        from gui.dashboard import Dashboard
        dashboard = Dashboard()
        dashboard.run()

    def is_authenticated(self) -> bool:
        return self._authenticated


def launch():
    LoginWindow()


if __name__ == "__main__":
    launch()
