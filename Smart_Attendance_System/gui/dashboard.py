"""
gui/dashboard.py - Main dashboard window for Smart Attendance System
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import os
import sys

# Allow imports from the project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import (APP_TITLE, APP_GEOMETRY, PRIMARY_COLOR, SECONDARY_COLOR,
                    ACCENT_COLOR, BG_COLOR, CARD_COLOR, TEXT_COLOR,
                    MUTED_COLOR, SUCCESS_COLOR, ERROR_COLOR, FONT_FAMILY,
                    LOGO_PATH, DATASET_DIR)
from database import (get_summary_stats, get_attendance_today, get_all_students,
                      initialize_database)
from train_model import train_face_model, model_exists


class Dashboard:
    """Main application window."""

    def __init__(self):
        initialize_database()
        self.root = tk.Tk()
        self.root.title(APP_TITLE)
        self.root.geometry(APP_GEOMETRY)
        self.root.configure(bg=BG_COLOR)
        self.root.resizable(True, True)
        self._build_ui()

    def run(self):
        self._refresh_stats()
        self.root.mainloop()

    # ── UI construction ───────────────────────────────────────────────────────
    def _build_ui(self):
        self._build_sidebar()
        self._build_main_area()
        self._show_page("home")

    # Sidebar ─────────────────────────────────────────────────────────────────
    def _build_sidebar(self):
        sidebar = tk.Frame(self.root, bg=PRIMARY_COLOR, width=220)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        # Logo / title
        logo_frame = tk.Frame(sidebar, bg=SECONDARY_COLOR, pady=20)
        logo_frame.pack(fill="x")
        tk.Label(logo_frame, text="🎓", bg=SECONDARY_COLOR,
                 fg="white", font=(FONT_FAMILY, 28)).pack()
        tk.Label(logo_frame, text=APP_TITLE, bg=SECONDARY_COLOR,
                 fg="white", font=(FONT_FAMILY, 10, "bold"),
                 wraplength=180).pack(pady=(4, 0))

        # Navigation buttons
        nav_items = [
            ("🏠  Dashboard",       "home"),
            ("👤  Register Student", "register"),
            ("📷  Take Attendance",  "attendance"),
            ("🎤  Voice Attendance", "voice"),
            ("📊  Reports",         "reports"),
            ("👥  Students",        "students"),
            ("⚙️  Train Model",     "train"),
        ]
        self._nav_buttons: dict[str, tk.Button] = {}
        btn_frame = tk.Frame(sidebar, bg=PRIMARY_COLOR)
        btn_frame.pack(fill="both", expand=True, pady=(10, 0))

        for label, page in nav_items:
            btn = tk.Button(
                btn_frame, text=label, bg=PRIMARY_COLOR, fg="#C5CAE9",
                activebackground=ACCENT_COLOR, activeforeground="white",
                font=(FONT_FAMILY, 10), anchor="w", padx=20, pady=12,
                relief="flat", cursor="hand2",
                command=lambda p=page: self._show_page(p)
            )
            btn.pack(fill="x")
            btn.bind("<Enter>", lambda e, b=btn: b.config(
                bg=SECONDARY_COLOR, fg="white") if b.cget("bg") != ACCENT_COLOR else None)
            btn.bind("<Leave>", lambda e, b=btn: b.config(
                bg=PRIMARY_COLOR, fg="#C5CAE9") if b.cget("bg") != ACCENT_COLOR else None)
            self._nav_buttons[page] = btn

        # Logout
        tk.Button(sidebar, text="⬅  Logout", bg=ERROR_COLOR, fg="white",
                  font=(FONT_FAMILY, 10, "bold"), pady=12, relief="flat",
                  cursor="hand2",
                  command=self._logout).pack(fill="x", side="bottom", padx=10, pady=10)

    # Main area ───────────────────────────────────────────────────────────────
    def _build_main_area(self):
        self._main = tk.Frame(self.root, bg=BG_COLOR)
        self._main.pack(side="left", fill="both", expand=True)
        self._pages: dict[str, tk.Frame] = {}

    def _show_page(self, page_name: str):
        # Highlight nav button
        for name, btn in self._nav_buttons.items():
            btn.config(bg=ACCENT_COLOR if name == page_name else PRIMARY_COLOR,
                       fg="white" if name == page_name else "#C5CAE9")

        # Destroy previous page
        for w in self._main.winfo_children():
            w.destroy()

        # Build the requested page
        builders = {
            "home":       self._page_home,
            "register":   self._page_register,
            "attendance": self._page_attendance,
            "voice":      self._page_voice,
            "reports":    self._page_reports,
            "students":   self._page_students,
            "train":      self._page_train,
        }
        builder = builders.get(page_name)
        if builder:
            builder()

    # ── Pages ─────────────────────────────────────────────────────────────────

    # HOME ────────────────────────────────────────────────────────────────────
    def _page_home(self):
        frame = tk.Frame(self._main, bg=BG_COLOR)
        frame.pack(fill="both", expand=True, padx=30, pady=20)

        tk.Label(frame, text="Dashboard Overview", bg=BG_COLOR,
                 fg=PRIMARY_COLOR, font=(FONT_FAMILY, 18, "bold")).pack(anchor="w")
        tk.Label(frame, text="System summary for today", bg=BG_COLOR,
                 fg=MUTED_COLOR, font=(FONT_FAMILY, 10)).pack(anchor="w", pady=(2, 16))

        stats = get_summary_stats()

        # Stat cards
        cards_frame = tk.Frame(frame, bg=BG_COLOR)
        cards_frame.pack(fill="x")

        card_data = [
            ("Total Students",  stats["total_students"],  "👥", "#1565C0"),
            ("Present Today",   stats["present_today"],   "✅", "#2E7D32"),
            ("Absent Today",    stats["absent_today"],    "❌", "#C62828"),
            ("Departments",     stats["departments"],      "🏛️", "#4527A0"),
        ]
        for title, value, icon, color in card_data:
            self._stat_card(cards_frame, title, value, icon, color)

        # Recent attendance table
        tk.Label(frame, text="Today's Attendance", bg=BG_COLOR,
                 fg=PRIMARY_COLOR, font=(FONT_FAMILY, 13, "bold")).pack(
            anchor="w", pady=(24, 8))

        self._attendance_table(frame, get_attendance_today())

        # Refresh
        tk.Button(frame, text="⟳  Refresh", bg=PRIMARY_COLOR, fg="white",
                  font=(FONT_FAMILY, 9), relief="flat", cursor="hand2",
                  padx=12, pady=6,
                  command=lambda: [w.destroy() for w in self._main.winfo_children()]
                            or self._page_home()
                  ).pack(anchor="e", pady=(8, 0))

    def _stat_card(self, parent, title, value, icon, color):
        card = tk.Frame(parent, bg=CARD_COLOR, pady=18, padx=18,
                        relief="flat", bd=0, highlightthickness=1,
                        highlightbackground="#E0E0E0")
        card.pack(side="left", expand=True, fill="x", padx=8, pady=4)

        top = tk.Frame(card, bg=CARD_COLOR)
        top.pack(fill="x")
        tk.Label(top, text=icon, bg=CARD_COLOR,
                 font=(FONT_FAMILY, 22)).pack(side="left")
        tk.Label(top, text=str(value), bg=CARD_COLOR, fg=color,
                 font=(FONT_FAMILY, 28, "bold")).pack(side="right")
        tk.Label(card, text=title, bg=CARD_COLOR, fg=MUTED_COLOR,
                 font=(FONT_FAMILY, 10)).pack(anchor="w", pady=(4, 0))

    def _attendance_table(self, parent, records):
        cols = ("Student ID", "Name", "Department", "Time In", "Time Out", "Status")
        tree_frame = tk.Frame(parent, bg=CARD_COLOR)
        tree_frame.pack(fill="both", expand=True)

        tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=12)
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview.Heading", background=PRIMARY_COLOR,
                        foreground="white", font=(FONT_FAMILY, 10, "bold"))
        style.configure("Treeview", rowheight=28,
                        font=(FONT_FAMILY, 10), fieldbackground=CARD_COLOR)
        style.map("Treeview", background=[("selected", ACCENT_COLOR)])

        widths = [110, 180, 140, 90, 90, 90]
        for col, w in zip(cols, widths):
            tree.heading(col, text=col)
            tree.column(col, width=w, anchor="center")

        tree.tag_configure("present", background="#E8F5E9")
        tree.tag_configure("late",    background="#FFF9C4")
        tree.tag_configure("odd",     background="#FAFAFA")

        for idx, r in enumerate(records):
            status = r.get("status", "Present")
            tag    = "present" if status == "Present" else "late" if status == "Late" else "odd"
            tree.insert("", "end",
                        values=(r["student_id"], r["name"], r["department"],
                                r.get("time_in", "—"), r.get("time_out", "—"), status),
                        tags=(tag,))

        sb = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        tree.pack(fill="both", expand=True)

    # REGISTER ────────────────────────────────────────────────────────────────
    def _page_register(self):
        from gui.register import RegisterPage
        RegisterPage(self._main)

    # ATTENDANCE ──────────────────────────────────────────────────────────────
    def _page_attendance(self):
        from gui.attendance_window import AttendancePage
        AttendancePage(self._main)

    # VOICE ───────────────────────────────────────────────────────────────────
    def _page_voice(self):
        frame = tk.Frame(self._main, bg=BG_COLOR)
        frame.pack(fill="both", expand=True, padx=30, pady=20)

        tk.Label(frame, text="Voice Attendance", bg=BG_COLOR,
                 fg=PRIMARY_COLOR, font=(FONT_FAMILY, 18, "bold")).pack(anchor="w")
        tk.Label(frame, text="Mark attendance using voice recognition",
                 bg=BG_COLOR, fg=MUTED_COLOR, font=(FONT_FAMILY, 10)).pack(anchor="w")

        status_var = tk.StringVar(value="Click the button and speak clearly.")
        result_var = tk.StringVar()

        card = tk.Frame(frame, bg=CARD_COLOR, padx=40, pady=40)
        card.pack(expand=True, pady=40)

        tk.Label(card, text="🎤", bg=CARD_COLOR,
                 font=(FONT_FAMILY, 56)).pack()
        tk.Label(card, textvariable=status_var, bg=CARD_COLOR, fg=MUTED_COLOR,
                 font=(FONT_FAMILY, 11)).pack(pady=(10, 20))

        result_lbl = tk.Label(card, textvariable=result_var, bg=CARD_COLOR,
                              fg=SUCCESS_COLOR, font=(FONT_FAMILY, 11, "bold"),
                              wraplength=380)
        result_lbl.pack(pady=(0, 16))

        def _run_voice():
            from voice_recognition import mark_by_voice
            root = self.root
            status_var.set("🎙️  Recording… speak now!")
            result_var.set("")

            def _worker():
                outcome = mark_by_voice()

                def _update():
                    if outcome["recognized"] and outcome["attendance"]:
                        result_var.set(f"✅  {outcome['message']}")
                        result_lbl.config(fg=SUCCESS_COLOR)
                    else:
                        result_var.set(f"❌  {outcome['message']}")
                        result_lbl.config(fg=ERROR_COLOR)
                    status_var.set("Click the button and speak clearly.")

                root.after(0, _update)

            threading.Thread(target=_worker, daemon=True).start()

        tk.Button(card, text="🎤  Start Voice Recognition",
                  bg=ACCENT_COLOR, fg="white",
                  font=(FONT_FAMILY, 12, "bold"), relief="flat",
                  cursor="hand2", padx=20, pady=12,
                  command=_run_voice).pack()

    # REPORTS ─────────────────────────────────────────────────────────────────
    def _page_reports(self):
        from gui.report_window import ReportPage
        ReportPage(self._main)

    # STUDENTS ────────────────────────────────────────────────────────────────
    def _page_students(self):
        frame = tk.Frame(self._main, bg=BG_COLOR)
        frame.pack(fill="both", expand=True, padx=30, pady=20)

        # Header row
        header = tk.Frame(frame, bg=BG_COLOR)
        header.pack(fill="x")
        tk.Label(header, text="Students", bg=BG_COLOR, fg=PRIMARY_COLOR,
                 font=(FONT_FAMILY, 18, "bold")).pack(side="left")

        # Search bar
        search_var = tk.StringVar()
        search_entry = tk.Entry(header, textvariable=search_var,
                                font=(FONT_FAMILY, 11), relief="solid", bd=1,
                                width=28)
        search_entry.pack(side="right", padx=(0, 8))
        tk.Label(header, text="Search:", bg=BG_COLOR, fg=TEXT_COLOR,
                 font=(FONT_FAMILY, 10)).pack(side="right")

        cols = ("ID", "Student ID", "Name", "Department", "Course", "Email", "Face", "Voice")
        tree = ttk.Treeview(frame, columns=cols, show="headings", height=20)
        widths = [40, 110, 180, 130, 110, 180, 60, 60]
        for col, w in zip(cols, widths):
            tree.heading(col, text=col)
            tree.column(col, width=w, anchor="center")

        style = ttk.Style()
        style.configure("Treeview.Heading", background=PRIMARY_COLOR,
                        foreground="white", font=(FONT_FAMILY, 10, "bold"))

        sb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        tree.pack(fill="both", expand=True, pady=(12, 0))

        def _populate(query=""):
            tree.delete(*tree.get_children())
            from database import search_students, get_all_students
            students = search_students(query) if query else get_all_students()
            for s in students:
                tree.insert("", "end", values=(
                    s["id"], s["student_id"], s["name"], s["department"],
                    s.get("course", "—"), s.get("email", "—"),
                    "✅" if s.get("has_face") else "❌",
                    "✅" if s.get("has_voice") else "❌",
                ))

        search_var.trace_add("write", lambda *_: _populate(search_var.get()))
        _populate()

        # Delete button
        def _delete():
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("Select", "Select a student first.")
                return
            sid = tree.item(sel[0])["values"][1]
            if messagebox.askyesno("Confirm", f"Delete student {sid}?"):
                from database import delete_student
                delete_student(str(sid))
                _populate(search_var.get())
                messagebox.showinfo("Done", f"Student {sid} deleted.")

        tk.Button(frame, text="🗑  Delete Selected", bg=ERROR_COLOR, fg="white",
                  font=(FONT_FAMILY, 10), relief="flat", cursor="hand2",
                  padx=12, pady=6, command=_delete).pack(anchor="e", pady=8)

    # TRAIN ───────────────────────────────────────────────────────────────────
    def _page_train(self):
        frame = tk.Frame(self._main, bg=BG_COLOR)
        frame.pack(fill="both", expand=True, padx=30, pady=20)

        tk.Label(frame, text="Train Face Recognition Model", bg=BG_COLOR,
                 fg=PRIMARY_COLOR, font=(FONT_FAMILY, 18, "bold")).pack(anchor="w")
        tk.Label(frame, text="Rebuild the model from the registered dataset",
                 bg=BG_COLOR, fg=MUTED_COLOR, font=(FONT_FAMILY, 10)).pack(anchor="w")

        card = tk.Frame(frame, bg=CARD_COLOR, padx=40, pady=40)
        card.pack(expand=True, pady=30)

        model_status = "✅ Model exists" if model_exists() else "❌ No model yet"
        tk.Label(card, text=f"Status: {model_status}", bg=CARD_COLOR,
                 fg=TEXT_COLOR, font=(FONT_FAMILY, 11)).pack(pady=(0, 16))

        prog_var    = tk.StringVar(value="")
        progress_lb = tk.Label(card, textvariable=prog_var, bg=CARD_COLOR,
                               fg=MUTED_COLOR, font=(FONT_FAMILY, 10))
        progress_lb.pack()

        progress_bar = ttk.Progressbar(card, length=400, mode="indeterminate")
        progress_bar.pack(pady=10)

        result_var = tk.StringVar()
        result_lbl = tk.Label(card, textvariable=result_var, bg=CARD_COLOR,
                              font=(FONT_FAMILY, 11, "bold"), wraplength=400)
        result_lbl.pack(pady=(8, 16))

        def _train():
            root = self.root
            progress_bar.start(10)
            prog_var.set("Training in progress…")
            result_var.set("")

            def _worker():
                def _progress(i, n, sid):
                    root.after(0, lambda: prog_var.set(f"Processing {i}/{n}: {sid}"))

                ok, msg = train_face_model(progress_callback=_progress)

                def _done():
                    progress_bar.stop()
                    result_var.set(msg)
                    result_lbl.config(fg=SUCCESS_COLOR if ok else ERROR_COLOR)
                    prog_var.set("")

                root.after(0, _done)

            threading.Thread(target=_worker, daemon=True).start()

        tk.Button(card, text="▶  Train Model Now",
                  bg=PRIMARY_COLOR, fg="white",
                  font=(FONT_FAMILY, 12, "bold"), relief="flat",
                  cursor="hand2", padx=20, pady=12,
                  command=_train).pack()

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _refresh_stats(self):
        pass   # stats are fetched on page load

    def _logout(self):
        if messagebox.askyesno("Logout", "Are you sure you want to logout?"):
            self.root.destroy()
            from login import launch
            launch()
