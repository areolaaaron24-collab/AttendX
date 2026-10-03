import customtkinter as ctk
import sqlite3
import hashlib
import os
import secrets
import shutil
from datetime import datetime
from tkinter import messagebox, filedialog
from PIL import Image
from intro import run_intro
import qrcode
from fingerprint_system import FingerprintSystem
from face_registration import register_student_face
from face_system import find_student_by_face, validate_face_attendance
from teacher_face_registration import register_teacher_face


# ============================================================
# ATTENDX - SCHOOL ATTENDANCE MANAGEMENT SYSTEM
# ============================================================

APP_TITLE = "ATTENDX | School Attendance Management System"
DB_FILE = "attendance.db"
QR_FOLDER = "qr_codes"


# ============================================================
# COLORS
# ============================================================

BG = "#080B16"
CARD = "#111729"
CARD_2 = "#151C31"
WHITE = "#FFFFFF"
TEXT = "#AAB4D0"
MUTED = "#68738F"

PURPLE = "#7C5CFC"
PURPLE_HOVER = "#6949EA"

BORDER = "#202B46"

SUCCESS = "#53D88A"
ERROR = "#FF5C70"
WARNING = "#F5B942"

BLUE = "#4D8DFF"

# Current signed-in user context used by the animated UI helpers.
CURRENT_USER_NAME = ""
CURRENT_USER_ROLE = ""


# ============================================================
# DATABASE
# ============================================================

def get_connection():
    connection = sqlite3.connect(DB_FILE)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _base_create_database():
    os.makedirs(QR_FOLDER, exist_ok=True)

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            school_id TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            name TEXT NOT NULL,
            course TEXT NOT NULL,
            year TEXT NOT NULL,
            section TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS teachers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            teacher_id TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            name TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            teacher_id INTEGER NOT NULL,
            course TEXT NOT NULL,
            subject TEXT NOT NULL,
            section TEXT NOT NULL,
            year TEXT NOT NULL,
            day TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            FOREIGN KEY (teacher_id) REFERENCES teachers(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS student_classes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            schedule_id INTEGER NOT NULL,
            UNIQUE(student_id, schedule_id),
            FOREIGN KEY (student_id) REFERENCES students(id),
            FOREIGN KEY (schedule_id) REFERENCES schedules(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS qr_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            schedule_id INTEGER NOT NULL,
            token TEXT UNIQUE NOT NULL,
            qr_file TEXT,
            created_at TEXT NOT NULL,
            UNIQUE(student_id, schedule_id),
            FOREIGN KEY (student_id) REFERENCES students(id),
            FOREIGN KEY (schedule_id) REFERENCES schedules(id)
        )
    """)

    # --------------------------------------------------------
    # ATTENDANCE TABLE
    # --------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            schedule_id INTEGER NOT NULL,
            attendance_date TEXT NOT NULL,
            attendance_time TEXT NOT NULL,
            status TEXT NOT NULL,
            method TEXT NOT NULL,
            UNIQUE(student_id, schedule_id, attendance_date),
            FOREIGN KEY (student_id) REFERENCES students(id),
            FOREIGN KEY (schedule_id) REFERENCES schedules(id)
        )
    """)

    connection.commit()
    connection.close()


# ============================================================
# PASSWORD
# ============================================================

def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


# ============================================================
# GENERAL UI
# ============================================================

def animate_page_transition(app):
    """Highly visible AttendX page transition with moving accent bars."""
    try:
        width = max(app.winfo_width(), 900)
    except Exception:
        width = 1100

    try:
        glow = ctk.CTkFrame(app, width=1, height=4, fg_color=PURPLE, corner_radius=0)
        glow.place(x=0, y=0)

        glow2 = ctk.CTkFrame(app, width=1, height=2, fg_color=BLUE, corner_radius=0)
        glow2.place(x=0, y=5)

        def sweep(pos=1):
            if not glow.winfo_exists():
                return
            pos += max(width // 18, 35)
            if pos >= width:
                pos = width
            glow.configure(width=pos)
            glow2.configure(width=max(1, int(pos * 0.72)))
            if pos >= width:
                app.after(220, lambda: (glow.destroy(), glow2.destroy()))
            else:
                app.after(14, lambda: sweep(pos))

        sweep()
    except Exception:
        pass


def animate_widget_in(app, widget, delay=0, start_y=18, end_y=0, duration=280):
    """Slide a widget down into place so dashboard sections visibly animate."""
    try:
        def start():
            if not widget.winfo_exists():
                return
            steps = max(8, duration // 20)
            current = 0

            def step():
                nonlocal current
                if not widget.winfo_exists():
                    return
                current += 1
                progress = current / steps
                eased = 1 - (1 - progress) ** 3
                y = int(start_y + (end_y - start_y) * eased)
                widget.pack_configure(pady=(y, 0))
                if current < steps:
                    app.after(20, step)
                else:
                    widget.pack_configure(pady=(0, 0))
            step()
        app.after(delay, start)
    except Exception:
        pass


def animate_number(app, label, target, delay=0):
    """Animated dashboard counters."""
    try:
        target = int(target)
        def begin():
            if not label.winfo_exists():
                return
            if target <= 0:
                label.configure(text="0")
                return
            steps = min(max(target, 8), 24)
            current = 0
            def step():
                nonlocal current
                if not label.winfo_exists():
                    return
                current += 1
                value = round(target * (current / steps))
                label.configure(text=str(value))
                if current < steps:
                    app.after(28, step)
            step()
        app.after(delay, begin)
    except Exception:
        pass


def show_greeting(app, name, role):
    """Animated welcome-back toast shown after a successful login."""
    try:
        toast = ctk.CTkFrame(
            app,
            width=330,
            height=78,
            corner_radius=14,
            fg_color=CARD_2,
            border_width=1,
            border_color=PURPLE
        )
        toast.place(relx=1.0, rely=0.10, anchor="ne", x=360)
        toast.pack_propagate(False)

        hour = datetime.now().hour
        if hour < 12:
            greeting = "GOOD MORNING, " + name.upper() + "! ☀️"
            message = "Ready to start a productive day on AttendX?"
        elif hour < 18:
            greeting = "GOOD AFTERNOON, " + name.upper() + "! ✨"
            message = "Welcome back. Let's keep things on track."
        else:
            greeting = "GOOD EVENING, " + name.upper() + "! 🌙"
            message = "Welcome back. Your AttendX account is ready."

        title = ctk.CTkLabel(
            toast,
            text=greeting,
            font=("Arial", 15, "bold"),
            text_color=WHITE
        )
        title.pack(anchor="w", padx=18, pady=(12, 0))

        subtitle = ctk.CTkLabel(
            toast,
            text=message,
            font=("Arial", 10),
            text_color=TEXT
        )
        subtitle.pack(anchor="w", padx=18, pady=(3, 0))

        def slide_in(x=360):
            if not toast.winfo_exists():
                return
            x -= 35
            if x <= 15:
                toast.place_configure(x=15)
                app.after(2800, slide_out)
            else:
                toast.place_configure(x=x)
                app.after(18, lambda: slide_in(x))

        def slide_out(x=15):
            if not toast.winfo_exists():
                return
            x += 35
            if x >= 360:
                toast.destroy()
            else:
                toast.place_configure(x=x)
                app.after(18, lambda: slide_out(x))

        app.after(60, slide_in)
    except Exception:
        pass


def animate_page_slide(app):
    """Lightweight vertical slide accent used on every page change."""
    try:
        width = max(app.winfo_width(), 900)
        panel = ctk.CTkFrame(
            app, width=width, height=4, fg_color=PURPLE, corner_radius=0
        )
        panel.place(x=0, y=0)

        def down(y=0):
            if not panel.winfo_exists():
                return
            y += 16
            if y >= 86:
                panel.place_forget()
                panel.destroy()
                return
            panel.place_configure(y=y)
            app.after(18, lambda: down(y))

        down()
    except Exception:
        pass


def show_context_greeting(app, title=""):
    """Show a short contextual greeting whenever a signed-in user opens a page."""
    try:
        if CURRENT_USER_NAME:
            context = title.upper().strip()
            messages = {
                "ADD MY SUBJECT": "Let's connect you to the right class.",
                "MY SUBJECTS": "Here are your enrolled classes.",
                "MY ATTENDANCE": "Here is your attendance history.",
                "MY PROFILE": "Your AttendX profile is ready.",
                "ADD SCHEDULE": "Let's build your class schedule.",
                "MY SCHEDULE": "Here is your schedule overview.",
                "SCHEDULE": "Here is your schedule overview.",
                "MY STUDENTS": "Your connected students are ready to view.",
                "ATTENDANCE CENTER": "Attendance tools are ready.",
                "ATTENDANCE": "Attendance tools are ready.",
                "ATTENDANCE RECORDS": "Your attendance records are ready.",
                "QR ATTENDANCE": "QR verification is ready when you are.",
                "TEACHER PORTAL": "Welcome to your Teacher / TC workspace.",
                "STUDENT PORTAL": "Welcome to your Student workspace.",
                "CREATE STUDENT ACCOUNT": "Let's get your AttendX account ready.",
                "CREATE TEACHER ACCOUNT": "Let's set up your Teacher / TC account.",
                "FORGOT PASSWORD": "Let's safely update your password.",
            }
            message = messages.get(context, "Your AttendX workspace is ready.")
            # Keep the page feedback, but avoid showing another full welcome toast on every page.
            app.after(120, lambda: show_small_status_toast(app, message))
        else:
            if title:
                show_small_status_toast(app, title.title() + " is ready.")
    except Exception:
        pass


def show_small_status_toast(app, message):
    """Small animated status toast for page-to-page feedback."""
    try:
        toast = ctk.CTkFrame(
            app, width=300, height=42, corner_radius=12,
            fg_color=CARD, border_width=1, border_color=BORDER
        )
        toast.place(relx=1.0, rely=0.19, anchor="ne", x=320)
        toast.pack_propagate(False)

        dot = ctk.CTkLabel(toast, text="●", font=("Arial", 10, "bold"), text_color=PURPLE)
        dot.pack(side="left", padx=(14, 8))
        ctk.CTkLabel(
            toast, text=message, font=("Arial", 10, "bold"),
            text_color=TEXT, anchor="w"
        ).pack(side="left", fill="x", expand=True, padx=(0, 12))

        def slide_in(x=320):
            if not toast.winfo_exists():
                return
            x -= 28
            if x <= 12:
                toast.place_configure(x=12)
                app.after(1800, slide_out)
            else:
                toast.place_configure(x=x)
                app.after(16, lambda: slide_in(x))

        def slide_out(x=12):
            if not toast.winfo_exists():
                return
            x += 28
            if x >= 320:
                toast.destroy()
            else:
                toast.place_configure(x=x)
                app.after(16, lambda: slide_out(x))

        app.after(40, slide_in)
    except Exception:
        pass


def create_live_datetime(parent):
    """Live date and time card used by Student and Teacher dashboards."""
    card = ctk.CTkFrame(
        parent,
        fg_color=CARD,
        corner_radius=12,
        border_width=1,
        border_color=BORDER,
        width=190,
        height=66
    )
    card.pack_propagate(False)

    time_label = ctk.CTkLabel(
        card, text="", font=("Arial", 15, "bold"), text_color=WHITE
    )
    time_label.pack(pady=(8, 0))

    date_label = ctk.CTkLabel(
        card, text="", font=("Arial", 9, "bold"), text_color=MUTED
    )
    date_label.pack(pady=(0, 5))

    def update_clock():
        try:
            if not card.winfo_exists():
                return
            now = datetime.now()
            time_label.configure(text=now.strftime("%I:%M:%S %p"))
            date_label.configure(text=now.strftime("%A, %B %d, %Y"))
            card.after(1000, update_clock)
        except Exception:
            pass

    update_clock()
    return card


def clear_screen(app):
    for widget in app.winfo_children():
        widget.destroy()
    # Keep a single light page animation instead of stacking multiple transitions.
    animate_page_slide(app)


def create_top_bar(parent, app, show_back=False, back_command=None):
    top = ctk.CTkFrame(
        parent,
        fg_color=BG,
        height=80
    )
    top.pack(fill="x")
    top.pack_propagate(False)

    left = ctk.CTkFrame(top, fg_color="transparent")
    left.pack(side="left", padx=35)

    logo = ctk.CTkLabel(
        left,
        text="ATTENDX",
        font=("Arial", 23, "bold"),
        text_color=WHITE
    )
    logo.pack(side="left")

    subtitle = ctk.CTkLabel(
        left,
        text="  |  SCHOOL ATTENDANCE SYSTEM",
        font=("Arial", 11, "bold"),
        text_color=MUTED
    )
    subtitle.pack(side="left", pady=(5, 0))

    right = ctk.CTkFrame(top, fg_color="transparent")
    right.pack(side="right", padx=35)

    status_dot = ctk.CTkLabel(
        right,
        text="●",
        font=("Arial", 12),
        text_color=SUCCESS
    )
    status_dot.pack(side="left", padx=(0, 6))

    status = ctk.CTkLabel(
        right,
        text="SYSTEM ONLINE",
        font=("Arial", 10, "bold"),
        text_color=SUCCESS
    )
    status.pack(side="left")

    # Subtle online-status pulse.
    def pulse_status(step=0):
        try:
            if not status_dot.winfo_exists():
                return
            if step % 2 == 0:
                status_dot.configure(text_color=SUCCESS)
                status.configure(text_color=SUCCESS)
            else:
                status_dot.configure(text_color="#86E7AD")
                status.configure(text_color="#86E7AD")
            app.after(900, lambda: pulse_status(step + 1))
        except Exception:
            pass

    app.after(900, pulse_status)

    if show_back:
        back_button = ctk.CTkButton(
            top,
            text="← BACK",
            width=100,
            height=34,
            corner_radius=8,
            fg_color=CARD,
            hover_color=CARD_2,
            border_width=1,
            border_color=BORDER,
            text_color=TEXT,
            command=back_command
        )
        back_button.pack(side="right", padx=(0, 20))

    return top


def create_page_title(parent, title, subtitle=""):
    frame = ctk.CTkFrame(parent, fg_color="transparent")
    frame.pack(fill="x", padx=60, pady=(25, 15))

    ctk.CTkLabel(
        frame,
        text=title,
        font=("Arial", 28, "bold"),
        text_color=WHITE
    ).pack(anchor="w")

    if subtitle:
        ctk.CTkLabel(
            frame,
            text=subtitle,
            font=("Arial", 12),
            text_color=MUTED
        ).pack(anchor="w", pady=(5, 0))

    animate_widget_in(parent.winfo_toplevel(), frame, delay=30, start_y=16, end_y=0, duration=260)
    parent.winfo_toplevel().after(120, lambda: show_context_greeting(parent.winfo_toplevel(), title))

    return frame


def create_input(parent, placeholder, show=None):
    entry = ctk.CTkEntry(
        parent,
        height=44,
        corner_radius=8,
        fg_color=CARD_2,
        border_color=BORDER,
        text_color=WHITE,
        placeholder_text=placeholder,
        placeholder_text_color=MUTED,
        show=show
    )
    entry.pack(fill="x", pady=6)
    return entry


def create_button(parent, text, command, width=180, height=42,
                  fg_color=PURPLE, hover_color=PURPLE_HOVER):
    button = ctk.CTkButton(
        parent,
        text=text,
        command=command,
        width=width,
        height=height,
        corner_radius=8,
        fg_color=fg_color,
        hover_color=hover_color,
        text_color=WHITE,
        font=("Arial", 11, "bold")
    )

    # Small press animation makes ordinary buttons feel consistent with the page transitions.
    def press(_event=None):
        try:
            button.configure(border_width=1, border_color=WHITE)
            button.after(110, lambda: button.configure(border_width=0))
        except Exception:
            pass
    button.bind("<ButtonPress-1>", press)
    return button


# ============================================================
# USER GUIDE
# ============================================================

def show_user_guide(app):
    guide = ctk.CTkToplevel(app)
    guide.title("ATTENDX | User Guide")
    guide.geometry("780x620")
    guide.resizable(False, False)
    guide.configure(fg_color=BG)
    guide.transient(app)
    guide.grab_set()

    header = ctk.CTkFrame(guide, fg_color=CARD, height=105, corner_radius=0)
    header.pack(fill="x")
    header.pack_propagate(False)

    ctk.CTkLabel(
        header,
        text="ATTENDX USER GUIDE",
        font=("Arial", 25, "bold"),
        text_color=WHITE
    ).pack(anchor="w", padx=30, pady=(22, 2))

    ctk.CTkLabel(
        header,
        text="A quick guide before you choose your account type.",
        font=("Arial", 11),
        text_color=MUTED
    ).pack(anchor="w", padx=30)

    body = ctk.CTkScrollableFrame(guide, fg_color="transparent")
    body.pack(fill="both", expand=True, padx=25, pady=18)

    sections = [
        (
            "STUDENT",
            "For students who want to manage subjects and check attendance.",
            [
                "1. Choose STUDENT on the first page.",
                "2. Create an account using your School ID, name, course, year and section.",
                "3. Log in using your School ID and password.",
                "4. Use ADD MY SUBJECT to connect to your teacher's class.",
                "5. MY SUBJECTS shows the classes you joined.",
                "6. MY ATTENDANCE shows your attendance records.",
                "7. MY PROFILE shows your account information and QR codes.",
            ]
        ),
        (
            "TEACHER / TC",
            "For teachers or class advisers who manage schedules, students and attendance.",
            [
                "1. Choose TEACHER on the first page.",
                "2. Create an account using your Teacher ID, name and password.",
                "3. Log in using your Teacher ID and password.",
                "4. ADD SCHEDULE to record your classes and schedule.",
                "5. MY STUDENTS shows students connected to your classes.",
                "6. ATTENDANCE CENTER lets you verify and record attendance.",
                "7. The Teacher Dashboard gives you attendance and schedule references.",
            ]
        )
    ]

    for title, description, steps in sections:
        card = ctk.CTkFrame(
            body,
            fg_color=CARD,
            corner_radius=14,
            border_width=1,
            border_color=BORDER
        )
        card.pack(fill="x", pady=7)

        ctk.CTkLabel(
            card,
            text=title,
            font=("Arial", 17, "bold"),
            text_color=PURPLE
        ).pack(anchor="w", padx=20, pady=(15, 3))

        ctk.CTkLabel(
            card,
            text=description,
            font=("Arial", 10),
            text_color=MUTED,
            wraplength=680,
            justify="left"
        ).pack(anchor="w", padx=20, pady=(0, 8))

        for step in steps:
            ctk.CTkLabel(
                card,
                text=step,
                font=("Arial", 10),
                text_color=TEXT,
                wraplength=680,
                justify="left"
            ).pack(anchor="w", padx=20, pady=2)

        ctk.CTkFrame(card, height=12, fg_color="transparent").pack()

    create_button(
        guide,
        "GOT IT",
        guide.destroy,
        width=180,
        height=40
    ).pack(pady=(0, 18))


# ============================================================
# ROLE SELECTION
# ============================================================

def student_portal(app):
    clear_screen(app)
    create_top_bar(
        app,
        app,
        True,
        lambda: role_selection(app)
    )

    create_page_title(
        app,
        "STUDENT PORTAL",
        "Access your student account and attendance information."
    )

    box = ctk.CTkFrame(
        app,
        width=500,
        height=360,
        fg_color=CARD,
        corner_radius=18,
        border_width=1,
        border_color=BORDER
    )
    box.pack(expand=True)
    box.pack_propagate(False)

    ctk.CTkLabel(
        box,
        text="Student Account",
        font=("Arial", 23, "bold"),
        text_color=WHITE
    ).pack(pady=(35, 20))

    create_button(
        box,
        "CREATE ACCOUNT",
        lambda: student_register_page(app),
        width=300
    ).pack(pady=8)

    create_button(
        box,
        "LOG IN",
        lambda: student_login_page(app),
        width=300
    ).pack(pady=8)

    ctk.CTkLabel(
        box,
        text="Create an account first if you are a new student.",
        font=("Arial", 11),
        text_color=MUTED
    ).pack(pady=20)


# ============================================================
# STUDENT REGISTER
# ============================================================

def student_login_page(app):
    clear_screen(app)

    create_top_bar(
        app,
        app,
        True,
        lambda: student_portal(app)
    )

    create_page_title(
        app,
        "STUDENT LOGIN",
        "Login using your School ID and password."
    )

    form = ctk.CTkFrame(
        app,
        width=500,
        height=360,
        fg_color=CARD,
        corner_radius=18,
        border_width=1,
        border_color=BORDER
    )
    form.pack(expand=True)
    form.pack_propagate(False)

    ctk.CTkLabel(
        form,
        text="Welcome Back",
        font=("Arial", 24, "bold"),
        text_color=WHITE
    ).pack(pady=(35, 20))

    school_id = create_input(form, "School ID")
    password = create_input(form, "Password", show="*")

    def login():
        sid = school_id.get().strip()
        password_value = password.get()

        if not sid or not password_value:
            messagebox.showerror(
                "Login Error",
                "Please enter your School ID and password."
            )
            return

        connection = get_connection()

        cursor = connection.cursor()

        cursor.execute("""
            SELECT id, school_id, name, course, year, section
            FROM students
            WHERE school_id = ? AND password = ?
        """, (
            sid,
            hash_password(password_value)
        ))

        student = cursor.fetchone()
        connection.close()

        if student:
            global CURRENT_USER_NAME, CURRENT_USER_ROLE
            CURRENT_USER_NAME = student[2]
            CURRENT_USER_ROLE = "student"
            student_dashboard(app, student)
        else:
            messagebox.showerror(
                "Login Failed",
                "Invalid School ID or password."
            )

    create_button(
        form,
        "LOG IN",
        login,
        width=300
    ).pack(pady=(15, 8))

    create_button(
        form,
        "FORGOT PASSWORD",
        lambda: student_forgot_password(app),
        width=300,
        fg_color="#242B40",
        hover_color="#323B55"
    ).pack(pady=5)


# ============================================================
# STUDENT FORGOT PASSWORD
# ============================================================

def student_forgot_password(app):
    clear_screen(app)

    create_top_bar(
        app,
        app,
        True,
        lambda: student_login_page(app)
    )

    create_page_title(
        app,
        "FORGOT PASSWORD",
        "Verify your School ID before changing the password."
    )

    form = ctk.CTkFrame(
        app,
        width=500,
        height=390,
        fg_color=CARD,
        corner_radius=18,
        border_width=1,
        border_color=BORDER
    )
    form.pack(expand=True)
    form.pack_propagate(False)

    school_id = create_input(form, "School ID")
    new_password = create_input(form, "New Password", show="*")
    confirm = create_input(form, "Confirm New Password", show="*")

    def reset_password():
        sid = school_id.get().strip()
        new_pass = new_password.get()
        confirm_pass = confirm.get()

        if not sid or not new_pass or not confirm_pass:
            messagebox.showerror(
                "Error",
                "Please complete all fields."
            )
            return

        if len(new_pass) < 6:
            messagebox.showerror(
                "Error",
                "Password must contain at least 6 characters."
            )
            return

        if new_pass != confirm_pass:
            messagebox.showerror(
                "Error",
                "Passwords do not match."
            )
            return

        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            "SELECT id FROM students WHERE school_id = ?",
            (sid,)
        )

        student = cursor.fetchone()

        if not student:
            connection.close()

            messagebox.showerror(
                "Error",
                "School ID does not exist."
            )
            return

        cursor.execute("""
            UPDATE students
            SET password = ?
            WHERE school_id = ?
        """, (
            hash_password(new_pass),
            sid
        ))

        connection.commit()
        connection.close()

        messagebox.showinfo(
            "Password Updated",
            "Your password has been successfully changed."
        )

        student_login_page(app)

    create_button(
        form,
        "RESET PASSWORD",
        reset_password,
        width=300
    ).pack(pady=30)


# ============================================================
# STUDENT DASHBOARD
# ============================================================

def student_add_subject_page(app, student):
    clear_screen(app)

    create_top_bar(
        app,
        app,
        True,
        lambda: student_dashboard(app, student)
    )

    create_page_title(
        app,
        "ADD MY SUBJECT",
        "Enter your teacher's name to find matching classes."
    )

    form = ctk.CTkFrame(
        app,
        width=700,
        height=650,
        fg_color=CARD,
        corner_radius=18,
        border_width=1,
        border_color=BORDER
    )

    form.pack(expand=True)
    form.pack_propagate(False)

    ctk.CTkLabel(
        form,
        text="Class Matching",
        font=("Arial", 23, "bold"),
        text_color=WHITE
    ).pack(
        pady=(25, 5)
    )

    ctk.CTkLabel(
        form,
        text="The system checks Teacher + Course + Year + Section.",
        font=("Arial", 11),
        text_color=MUTED
    ).pack(
        pady=(0, 15)
    )

    # =========================================================
    # TEACHER NAME INPUT
    # =========================================================

    # =========================================================
    # SEARCH BAR + SEARCH BUTTON
    # =========================================================

    search_bar = ctk.CTkFrame(
        form,
        fg_color="transparent"
    )
    search_bar.pack(
        fill="x",
        padx=25,
        pady=(5, 10)
    )

    teacher_name = create_input(
        search_bar,
        "Teacher Name"
    )
    teacher_name.pack(
        side="left",
        fill="x",
        expand=True,
        padx=(0, 10)
    )

    # =========================================================
    # SELECTED SCHEDULE
    # =========================================================

    selected_schedule = {
        "id": None
    }

    selected_panel = ctk.CTkFrame(
        form,
        fg_color=CARD_2,
        corner_radius=10,
        border_width=1,
        border_color=BORDER,
        height=82
    )
    selected_panel.pack(
        fill="x",
        padx=25,
        pady=(0, 8)
    )
    selected_panel.pack_propagate(False)

    selected_label = ctk.CTkLabel(
        selected_panel,
        text="No class selected.",
        font=("Arial", 11, "bold"),
        text_color=MUTED,
        wraplength=470,
        justify="left",
        anchor="w"
    )
    selected_label.pack(
        side="left",
        fill="both",
        expand=True,
        padx=15,
        pady=8
    )

    # This button stays in a fixed area. It will NOT move when
    # the selected schedule information becomes longer.
    add_selected_button = create_button(
        selected_panel,
        "ADD SELECTED",
        None,
        width=145,
        height=38,
        fg_color=SUCCESS,
        hover_color=SUCCESS
    )
    add_selected_button.pack(
        side="right",
        padx=12
    )

    # =========================================================
    # SEARCH RESULTS
    # =========================================================

    results_frame = ctk.CTkScrollableFrame(
        form,
        width=600,
        height=270,
        fg_color=CARD_2
    )

    # IMPORTANT:
    # Do not use expand=True here.
    # This keeps the buttons below visible.
    results_frame.pack(
        padx=25,
        pady=(0, 10),
        fill="both",
        expand=True
    )

    # =========================================================
    # CLEAR RESULTS
    # =========================================================

    def clear_results():

        for widget in results_frame.winfo_children():
            widget.destroy()

    # =========================================================
    # SELECT CLASS
    # =========================================================

    def select_class(
        schedule_id,
        schedule_info,
        selected_button
    ):

        # Save selected schedule ID
        selected_schedule["id"] = schedule_id

        # Show selected schedule
        selected_label.configure(
            text=(
                "SELECTED CLASS:\n"
                + schedule_info
            ),
            text_color=SUCCESS
        )

        # Reset all SELECT buttons
        for widget in results_frame.winfo_children():

            if not isinstance(
                widget,
                ctk.CTkFrame
            ):
                continue

            for child in widget.winfo_children():

                if isinstance(
                    child,
                    ctk.CTkButton
                ):

                    child.configure(
                        text="SELECT",
                        fg_color=PURPLE,
                        hover_color=PURPLE_HOVER
                    )

        # Mark selected button
        selected_button.configure(
            text="SELECTED",
            fg_color=SUCCESS,
            hover_color=SUCCESS
        )

    # =========================================================
    # SEARCH CLASSES
    # =========================================================

    def search_classes():

        clear_results()

        selected_schedule["id"] = None

        selected_label.configure(
            text="No class selected.",
            text_color=MUTED
        )

        teacher_value = teacher_name.get().strip()

        # -----------------------------------------------------
        # CHECK TEACHER INPUT
        # -----------------------------------------------------

        if not teacher_value:

            messagebox.showerror(
                "Error",
                "Please enter the Teacher Name."
            )

            return

        connection = get_connection()
        cursor = connection.cursor()

        try:

            # -------------------------------------------------
            # FIND TEACHER
            #
            # LIKE allows partial searching.
            #
            # Example:
            #
            # Registered:
            # Juan Dela Cruz
            #
            # Student types:
            # Juan
            #
            # The teacher can still be found.
            # -------------------------------------------------

            cursor.execute("""
                SELECT
                    id,
                    teacher_id,
                    name
                FROM teachers
                WHERE LOWER(TRIM(name)) LIKE LOWER(TRIM(?))
                ORDER BY name
            """, (
                "%" + teacher_value + "%",
            ))

            teacher_records = cursor.fetchall()

            # -------------------------------------------------
            # TEACHER NOT FOUND
            # -------------------------------------------------

            if not teacher_records:

                selected_label.configure(
                    text="Teacher not found.",
                    text_color=ERROR
                )

                ctk.CTkLabel(
                    results_frame,
                    text=(
                        "TEACHER NOT FOUND\n\n"
                        "No registered teacher matches:\n"
                        + teacher_value
                        + "\n\n"
                        "Please check the teacher's registered name."
                    ),
                    text_color=ERROR,
                    font=("Arial", 12, "bold"),
                    justify="center"
                ).pack(
                    pady=35
                )

                return

            # -------------------------------------------------
            # FIND MATCHING SCHEDULES
            #
            # We use the teacher IDs found above.
            #
            # Course + Year + Section must still match
            # the logged-in student.
            # -------------------------------------------------

            matching_schedules = []

            for teacher_record in teacher_records:

                cursor.execute("""
                    SELECT
                        schedules.id,
                        schedules.subject,
                        schedules.course,
                        schedules.year,
                        schedules.section,
                        schedules.day,
                        schedules.start_time,
                        schedules.end_time,
                        teachers.name,
                        teachers.teacher_id
                    FROM schedules
                    INNER JOIN teachers
                        ON schedules.teacher_id = teachers.id
                    WHERE schedules.teacher_id = ?
                      AND UPPER(TRIM(schedules.course))
                          = UPPER(TRIM(?))
                      AND UPPER(TRIM(schedules.year))
                          = UPPER(TRIM(?))
                      AND UPPER(TRIM(schedules.section))
                          = UPPER(TRIM(?))
                """, (
                    teacher_record[0],
                    student[3],
                    student[4],
                    student[5]
                ))

                rows = cursor.fetchall()

                for row in rows:
                    matching_schedules.append(row)

            # -------------------------------------------------
            # NO MATCHING SCHEDULE
            # -------------------------------------------------

            if not matching_schedules:

                selected_label.configure(
                    text="Teacher found, but no matching class.",
                    text_color=WARNING
                )

                ctk.CTkLabel(
                    results_frame,
                    text=(
                        "TEACHER FOUND\n\n"
                        "But there is no schedule that matches "
                        "your information.\n\n"
                        "YOUR INFORMATION\n"
                        "Course: "
                        + str(student[3])
                        + "\n"
                        + "Year: "
                        + str(student[4])
                        + "\n"
                        + "Section: "
                        + str(student[5])
                        + "\n\n"
                        + "The teacher's schedule must have the "
                        "same Course, Year and Section."
                    ),
                    text_color=WARNING,
                    font=("Arial", 12),
                    justify="center"
                ).pack(
                    pady=30
                )

                return

            # -------------------------------------------------
            # SORT SCHEDULES
            # -------------------------------------------------

            def schedule_sort_key(item):

                day_order = {
                    "Monday": 1,
                    "Tuesday": 2,
                    "Wednesday": 3,
                    "Thursday": 4,
                    "Friday": 5
                }

                return (
                    day_order.get(
                        item[5],
                        6
                    ),
                    item[6]
                )

            matching_schedules.sort(
                key=schedule_sort_key
            )

            # -------------------------------------------------
            # SHOW NUMBER OF RESULTS
            # -------------------------------------------------

            selected_label.configure(
                text=(
                    str(len(matching_schedules))
                    + " matching class/s found."
                ),
                text_color=SUCCESS
            )

            ctk.CTkLabel(
                results_frame,
                text="MATCHING CLASSES",
                font=("Arial", 12, "bold"),
                text_color=SUCCESS
            ).pack(
                anchor="w",
                padx=15,
                pady=10
            )

            # -------------------------------------------------
            # DISPLAY MATCHING SCHEDULES
            # -------------------------------------------------

            for item in matching_schedules:

                schedule_id = item[0]

                row = ctk.CTkFrame(
                    results_frame,
                    fg_color=CARD,
                    corner_radius=10,
                    border_width=1,
                    border_color=BORDER
                )

                row.pack(
                    fill="x",
                    padx=8,
                    pady=5
                )

                # -------------------------------------------------
                # SCHEDULE SHORT INFORMATION
                # -------------------------------------------------

                info = (
                    str(item[1])
                    + " | "
                    + str(item[2])
                    + " | "
                    + str(item[3])
                    + " | Section "
                    + str(item[4])
                    + "\n"
                    + str(item[5])
                    + "  "
                    + format_time_12h(str(item[6]))
                    + " - "
                    + format_time_12h(str(item[7]))
                )

                ctk.CTkLabel(
                    row,
                    text=info,
                    font=("Arial", 11),
                    text_color=WHITE,
                    justify="left"
                ).pack(
                    side="left",
                    padx=15,
                    pady=10
                )

                # -------------------------------------------------
                # FULL SCHEDULE INFORMATION
                # -------------------------------------------------

                schedule_info = (
                    "Subject: "
                    + str(item[1])
                    + "\n"
                    + "Teacher: "
                    + str(item[8])
                    + "\n"
                    + "Course: "
                    + str(item[2])
                    + "\n"
                    + "Year: "
                    + str(item[3])
                    + "\n"
                    + "Section: "
                    + str(item[4])
                    + "\n"
                    + "Schedule: "
                    + str(item[5])
                    + " "
                    + format_time_12h(str(item[6]))
                    + " - "
                    + format_time_12h(str(item[7]))
                )

                # -------------------------------------------------
                # SELECT BUTTON
                # -------------------------------------------------

                select_button = create_button(
                    row,
                    "SELECT",
                    None,
                    width=100,
                    height=35
                )

                # -------------------------------------------------
                # IMPORTANT:
                # Save the current button inside the lambda.
                # This prevents every button from selecting
                # the last schedule.
                # -------------------------------------------------

                select_button.configure(
                    command=lambda
                    sid=schedule_id,
                    info=schedule_info,
                    button=select_button:
                        select_class(
                            sid,
                            info,
                            button
                        )
                )

                # -------------------------------------------------
                # ADD SUBJECT BUTTON
                # -------------------------------------------------
                # Each searched schedule has its own ADD button.
                # This prevents the student from losing the add
                # action after selecting a schedule.
                # -------------------------------------------------

                add_button = create_button(
                    row,
                    "ADD",
                    None,
                    width=85,
                    height=35,
                    fg_color=SUCCESS,
                    hover_color=SUCCESS
                )

                add_button.configure(
                    command=lambda sid=schedule_id:
                        add_subject(sid)
                )

                add_button.pack(
                    side="right",
                    padx=(0, 8)
                )

                select_button.pack(
                    side="right",
                    padx=8
                )

        except Exception as error:

            messagebox.showerror(
                "Search Error",
                "Unable to search for the class.\n\n"
                + str(error)
            )

        finally:

            connection.close()

    # =========================================================
    # ADD SUBJECT
    # =========================================================

    def add_subject(schedule_id_override=None):

        # The selected schedule can come from the SELECT button
        # or directly from the ADD SUBJECT button on a schedule row.
        if schedule_id_override is not None:
            selected_schedule["id"] = schedule_id_override

        schedule_id = selected_schedule["id"]

        # -----------------------------------------------------
        # CHECK SELECTED CLASS
        # -----------------------------------------------------

        if schedule_id is None:

            messagebox.showerror(
                "No Class Selected",
                "Please search for a class and select a schedule first."
            )

            return

        connection = get_connection()
        cursor = connection.cursor()

        try:

            # -------------------------------------------------
            # GET CURRENT STUDENT
            # -------------------------------------------------

            cursor.execute("""
                SELECT
                    id,
                    course,
                    year,
                    section
                FROM students
                WHERE id = ?
            """, (
                student[0],
            ))

            current_student = cursor.fetchone()

            if not current_student:

                messagebox.showerror(
                    "Error",
                    "Student account could not be found."
                )

                return

            # -------------------------------------------------
            # GET SELECTED SCHEDULE
            # -------------------------------------------------

            cursor.execute("""
                SELECT
                    schedules.id,
                    schedules.teacher_id,
                    schedules.course,
                    schedules.year,
                    schedules.section,
                    schedules.subject,
                    schedules.day,
                    schedules.start_time,
                    schedules.end_time,
                    teachers.name
                FROM schedules
                INNER JOIN teachers
                    ON schedules.teacher_id = teachers.id
                WHERE schedules.id = ?
            """, (
                schedule_id,
            ))

            schedule = cursor.fetchone()

            if not schedule:

                selected_schedule["id"] = None

                selected_label.configure(
                    text="Selected class no longer exists.",
                    text_color=ERROR
                )

                messagebox.showerror(
                    "Error",
                    "The selected schedule no longer exists."
                )

                return

            # -------------------------------------------------
            # CHECK COURSE
            # -------------------------------------------------

            if (
                current_student[1].strip().upper()
                !=
                schedule[2].strip().upper()
            ):

                messagebox.showerror(
                    "Course Mismatch",
                    "The selected schedule does not match your course."
                )

                return

            # -------------------------------------------------
            # CHECK YEAR
            # -------------------------------------------------

            if (
                current_student[2].strip().upper()
                !=
                schedule[3].strip().upper()
            ):

                messagebox.showerror(
                    "Year Mismatch",
                    "The selected schedule does not match your year level."
                )

                return

            # -------------------------------------------------
            # CHECK SECTION
            # -------------------------------------------------

            if (
                current_student[3].strip().upper()
                !=
                schedule[4].strip().upper()
            ):

                messagebox.showerror(
                    "Section Mismatch",
                    "The selected schedule does not match your section."
                )

                return

            # -------------------------------------------------
            # CHECK IF ALREADY ADDED
            # -------------------------------------------------

            cursor.execute("""
                SELECT id
                FROM student_classes
                WHERE student_id = ?
                  AND schedule_id = ?
            """, (
                student[0],
                schedule_id
            ))

            existing = cursor.fetchone()

            if existing:

                messagebox.showwarning(
                    "Already Added",
                    "You are already connected to this class."
                )

                return

            # -------------------------------------------------
            # ADD STUDENT TO CLASS
            # -------------------------------------------------

            cursor.execute("""
                INSERT INTO student_classes
                (
                    student_id,
                    schedule_id
                )
                VALUES (?, ?)
            """, (
                student[0],
                schedule_id
            ))

            connection.commit()

            # -------------------------------------------------
            # SUCCESS
            # -------------------------------------------------

            messagebox.showinfo(
                "Subject Added",
                "Subject successfully added!\n\n"
                "Subject: "
                + schedule[5]
                + "\nTeacher: "
                + schedule[9]
                + "\nCourse: "
                + schedule[2]
                + "\nYear: "
                + schedule[3]
                + "\nSection: "
                + schedule[4]
                + "\nSchedule: "
                + schedule[6]
                + " "
                + format_time_12h(schedule[7])
                + " - "
                + format_time_12h(schedule[8])
            )

            # Open My Subjects immediately so the student can
            # verify that the class was actually saved.
            student_my_subjects_page(
                app,
                student
            )

        except sqlite3.IntegrityError:

            connection.rollback()

            messagebox.showerror(
                "Already Added",
                "You are already connected to this class."
            )

        except Exception as error:

            connection.rollback()

            messagebox.showerror(
                "Error",
                "Unable to add the selected subject.\n\n"
                + str(error)
            )

        finally:

            connection.close()

    # =========================================================
    # CONNECT THE FIXED TOP BUTTONS
    # =========================================================

    search_button = create_button(
        search_bar,
        "SEARCH",
        search_classes,
        width=115,
        height=40
    )
    search_button.pack(
        side="right"
    )

    add_selected_button.configure(
        command=add_subject
    )
# ============================================================
# STUDENT MY SUBJECTS
# ============================================================

def student_my_subjects_page(app, student):
    clear_screen(app)

    create_top_bar(
        app,
        app,
        True,
        lambda: student_dashboard(app, student)
    )

    create_page_title(
        app,
        "MY SUBJECTS",
        "Classes connected to your student account."
    )

    container = ctk.CTkScrollableFrame(
        app,
        fg_color="transparent"
    )
    container.pack(fill="both", expand=True, padx=60, pady=10)

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            schedules.subject,
            teachers.name,
            schedules.course,
            schedules.year,
            schedules.section,
            schedules.day,
            schedules.start_time,
            schedules.end_time
        FROM student_classes
        INNER JOIN schedules
            ON student_classes.schedule_id = schedules.id
        INNER JOIN teachers
            ON schedules.teacher_id = teachers.id
        WHERE student_classes.student_id = ?
        ORDER BY schedules.day, schedules.start_time
    """, (student[0],))

    subjects = cursor.fetchall()
    connection.close()

    if not subjects:
        ctk.CTkLabel(
            container,
            text="You have no subjects yet.",
            font=("Arial", 15),
            text_color=MUTED
        ).pack(pady=60)

        return

    for item in subjects:
        card = ctk.CTkFrame(
            container,
            fg_color=CARD,
            corner_radius=14,
            border_width=1,
            border_color=BORDER
        )
        card.pack(fill="x", pady=6)

        ctk.CTkLabel(
            card,
            text=item[0],
            font=("Arial", 19, "bold"),
            text_color=WHITE
        ).pack(anchor="w", padx=20, pady=(15, 3))

        ctk.CTkLabel(
            card,
            text="Teacher: " + item[1],
            font=("Arial", 11),
            text_color=TEXT
        ).pack(anchor="w", padx=20)

        ctk.CTkLabel(
            card,
            text=(
                item[2]
                + " | "
                + item[3]
                + " Year | Section "
                + item[4]
                + " | "
                + item[5]
                + " "
                + format_time_12h(item[6])
                + "-"
                + format_time_12h(item[7])
            ),
            font=("Arial", 11),
            text_color=MUTED
        ).pack(anchor="w", padx=20, pady=(3, 15))


# ============================================================
# STUDENT ATTENDANCE
# ============================================================

def student_attendance_page(app, student):
    clear_screen(app)

    create_top_bar(
        app,
        app,
        True,
        lambda: student_dashboard(app, student)
    )

    create_page_title(
        app,
        "MY ATTENDANCE",
        "Your attendance history."
    )

    container = ctk.CTkScrollableFrame(
        app,
        fg_color="transparent"
    )
    container.pack(fill="both", expand=True, padx=55, pady=10)

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            attendance.attendance_date,
            attendance.attendance_time,
            attendance.status,
            attendance.method,
            schedules.subject,
            teachers.name,
            schedules.course,
            schedules.year,
            schedules.section
        FROM attendance
        INNER JOIN schedules
            ON attendance.schedule_id = schedules.id
        INNER JOIN teachers
            ON schedules.teacher_id = teachers.id
        WHERE attendance.student_id = ?
        ORDER BY
            attendance.attendance_date DESC,
            attendance.attendance_time DESC
    """, (student[0],))

    records = cursor.fetchall()
    connection.close()

    if not records:
        box = ctk.CTkFrame(
            container,
            fg_color=CARD,
            corner_radius=15,
            border_width=1,
            border_color=BORDER
        )
        box.pack(fill="x", pady=20)

        ctk.CTkLabel(
            box,
            text="NO ATTENDANCE RECORDS",
            font=("Arial", 20, "bold"),
            text_color=WHITE
        ).pack(pady=(45, 10))

        ctk.CTkLabel(
            box,
            text="Your attendance records will appear here after verification.",
            font=("Arial", 12),
            text_color=MUTED
        ).pack(pady=(0, 45))

        return

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    present_count = 0
    late_count = 0
    absent_count = 0

    for record in records:
        if record[2] == "PRESENT":
            present_count += 1
        elif record[2] == "LATE":
            late_count += 1
        elif record[2] == "ABSENT":
            absent_count += 1

    summary = ctk.CTkFrame(
        container,
        fg_color="transparent"
    )
    summary.pack(fill="x", pady=(0, 12))

    summary_items = [
        ("TOTAL", str(len(records)), WHITE),
        ("PRESENT", str(present_count), SUCCESS),
        ("LATE", str(late_count), WARNING),
        ("ABSENT", str(absent_count), ERROR)
    ]

    for title, value, color in summary_items:
        card = ctk.CTkFrame(
            summary,
            fg_color=CARD,
            corner_radius=12,
            border_width=1,
            border_color=BORDER
        )
        card.pack(side="left", expand=True, fill="x", padx=5)

        ctk.CTkLabel(
            card,
            text=title,
            font=("Arial", 10, "bold"),
            text_color=MUTED
        ).pack(pady=(15, 3))

        ctk.CTkLabel(
            card,
            text=value,
            font=("Arial", 24, "bold"),
            text_color=color
        ).pack(pady=(0, 15))

    # --------------------------------------------------------
    # RECORDS
    # --------------------------------------------------------

    for record in records:
        card = ctk.CTkFrame(
            container,
            fg_color=CARD,
            corner_radius=14,
            border_width=1,
            border_color=BORDER
        )
        card.pack(fill="x", pady=6)

        top = ctk.CTkFrame(
            card,
            fg_color="transparent"
        )
        top.pack(fill="x", padx=20, pady=(15, 5))

        ctk.CTkLabel(
            top,
            text=record[4],
            font=("Arial", 17, "bold"),
            text_color=WHITE
        ).pack(side="left")

        status_color = SUCCESS

        if record[2] == "LATE":
            status_color = WARNING
        elif record[2] == "ABSENT":
            status_color = ERROR

        ctk.CTkLabel(
            top,
            text=record[2],
            font=("Arial", 11, "bold"),
            text_color=status_color
        ).pack(side="right")

        ctk.CTkLabel(
            card,
            text=(
                "Teacher: "
                + record[5]
                + "   |   "
                + record[6]
                + "   |   "
                + record[7]
                + " Year   |   Section "
                + record[8]
            ),
            font=("Arial", 11),
            text_color=TEXT
        ).pack(anchor="w", padx=20)

        ctk.CTkLabel(
            card,
            text=(
                "Date: "
                + record[0]
                + "   |   Time: "
                + record[1]
                + "   |   Method: "
                + record[3]
            ),
            font=("Arial", 10),
            text_color=MUTED
        ).pack(anchor="w", padx=20, pady=(4, 15))


# ============================================================
# QR HELPERS
# ============================================================

def create_qr_for_class(student_id, schedule_id):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id, token, qr_file
        FROM qr_codes
        WHERE student_id = ? AND schedule_id = ?
    """, (
        student_id,
        schedule_id
    ))

    existing = cursor.fetchone()

    if existing:
        connection.close()

        if existing[2] and os.path.exists(existing[2]):
            return existing[0], existing[1], existing[2]

        token = existing[1]
        filename = os.path.join(
            QR_FOLDER,
            "student_" + str(student_id)
            + "_class_" + str(schedule_id)
            + ".png"
        )

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4
        )

        qr.add_data(token)
        qr.make(fit=True)

        image = qr.make_image(
            fill_color="black",
            back_color="white"
        )

        image.save(filename)

        connection = get_connection()

        connection.execute("""
            UPDATE qr_codes
            SET qr_file = ?
            WHERE id = ?
        """, (
            filename,
            existing[0]
        ))

        connection.commit()
        connection.close()

        return existing[0], token, filename

    token = "ATTENDX-" + secrets.token_hex(16)

    filename = os.path.join(
        QR_FOLDER,
        "student_" + str(student_id)
        + "_class_" + str(schedule_id)
        + ".png"
    )

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4
    )

    qr.add_data(token)
    qr.make(fit=True)

    image = qr.make_image(
        fill_color="black",
        back_color="white"
    )

    image.save(filename)

    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        connection.execute("""
            INSERT INTO qr_codes
            (
                student_id,
                schedule_id,
                token,
                qr_file,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            student_id,
            schedule_id,
            token,
            filename,
            created_at
        ))

        connection.commit()

    except sqlite3.IntegrityError:
        connection.close()

        return create_qr_for_class(
            student_id,
            schedule_id
        )

    connection.close()

    return None, token, filename


def get_student_classes_with_qr(student_id):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            schedules.id,
            schedules.subject,
            teachers.name,
            schedules.course,
            schedules.year,
            schedules.section,
            schedules.day,
            schedules.start_time,
            schedules.end_time,
            qr_codes.token,
            qr_codes.qr_file,
            qr_codes.created_at
        FROM student_classes
        INNER JOIN schedules
            ON student_classes.schedule_id = schedules.id
        INNER JOIN teachers
            ON schedules.teacher_id = teachers.id
        LEFT JOIN qr_codes
            ON qr_codes.student_id = student_classes.student_id
           AND qr_codes.schedule_id = student_classes.schedule_id
        WHERE student_classes.student_id = ?
        ORDER BY schedules.day, schedules.start_time
    """, (student_id,))

    rows = cursor.fetchall()
    connection.close()

    return rows


# ============================================================
# STUDENT PROFILE
# ============================================================

def student_profile_page(app, student):
    clear_screen(app)

    create_top_bar(
        app,
        app,
        True,
        lambda: student_dashboard(app, student)
    )

    create_page_title(
        app,
        "MY PROFILE",
        "Manage your student information and verification methods."
    )

    main = ctk.CTkScrollableFrame(
        app,
        fg_color="transparent"
    )
    main.pack(fill="both", expand=True, padx=55, pady=5)

    # STUDENT INFORMATION

    info_card = ctk.CTkFrame(
        main,
        fg_color=CARD,
        corner_radius=15,
        border_width=1,
        border_color=BORDER
    )
    info_card.pack(fill="x", pady=8)

    ctk.CTkLabel(
        info_card,
        text="STUDENT INFORMATION",
        font=("Arial", 17, "bold"),
        text_color=WHITE
    ).pack(anchor="w", padx=25, pady=(20, 15))

    information = [
        ("School ID", student[1]),
        ("Full Name", student[2]),
        ("Course", student[3]),
        ("Year Level", student[4]),
        ("Section", student[5])
    ]

    for label, value in information:
        row = ctk.CTkFrame(
            info_card,
            fg_color=CARD_2,
            corner_radius=8
        )
        row.pack(fill="x", padx=20, pady=4)

        ctk.CTkLabel(
            row,
            text=label,
            width=150,
            anchor="w",
            font=("Arial", 11, "bold"),
            text_color=MUTED
        ).pack(side="left", padx=15, pady=10)

        ctk.CTkLabel(
            row,
            text=value,
            anchor="w",
            font=("Arial", 11),
            text_color=WHITE
        ).pack(side="left", padx=10)

    # QR SECTION

    qr_header = ctk.CTkFrame(
        main,
        fg_color=CARD,
        corner_radius=15,
        border_width=1,
        border_color=BORDER
    )
    qr_header.pack(fill="x", pady=8)

    ctk.CTkLabel(
        qr_header,
        text="QR VERIFICATION",
        font=("Arial", 17, "bold"),
        text_color=WHITE
    ).pack(anchor="w", padx=25, pady=(20, 5))

    ctk.CTkLabel(
        qr_header,
        text=(
            "Each enrolled class receives its own unique QR code. "
            "The QR contains a secure random token only."
        ),
        font=("Arial", 11),
        text_color=MUTED,
        wraplength=800
    ).pack(anchor="w", padx=25, pady=(0, 15))

    classes = get_student_classes_with_qr(student[0])

    if not classes:
        ctk.CTkLabel(
            qr_header,
            text="No enrolled subjects yet.",
            font=("Arial", 12),
            text_color=WARNING
        ).pack(pady=30)

    for item in classes:
        schedule_id = item[0]

        class_card = ctk.CTkFrame(
            qr_header,
            fg_color=CARD_2,
            corner_radius=10,
            border_width=1,
            border_color=BORDER
        )
        class_card.pack(fill="x", padx=20, pady=6)

        title_frame = ctk.CTkFrame(
            class_card,
            fg_color="transparent"
        )
        title_frame.pack(fill="x", padx=15, pady=(12, 5))

        ctk.CTkLabel(
            title_frame,
            text=item[1],
            font=("Arial", 16, "bold"),
            text_color=WHITE
        ).pack(side="left")

        if item[9]:
            ctk.CTkLabel(
                title_frame,
                text="QR READY",
                font=("Arial", 9, "bold"),
                text_color=SUCCESS
            ).pack(side="right")

        ctk.CTkLabel(
            class_card,
            text=(
                "Teacher: "
                + item[2]
                + "   |   "
                + item[3]
                + "   |   "
                + item[4]
                + " Year   |   Section "
                + item[5]
                + "   |   "
                + item[6]
                + " "
                + format_time_12h(item[7])
                + "-"
                + format_time_12h(item[8])
            ),
            font=("Arial", 10),
            text_color=TEXT
        ).pack(anchor="w", padx=15, pady=(0, 10))

        buttons = ctk.CTkFrame(
            class_card,
            fg_color="transparent"
        )
        buttons.pack(anchor="w", padx=15, pady=(0, 12))

        create_button(
            buttons,
            "GENERATE QR",
            lambda sid=schedule_id: generate_qr_action(
                app,
                student,
                sid
            ),
            width=130,
            height=35
        ).pack(side="left", padx=(0, 6))

        create_button(
            buttons,
            "VIEW QR",
            lambda sid=schedule_id: view_qr_action(
                app,
                student,
                sid
            ),
            width=110,
            height=35,
            fg_color="#242B40",
            hover_color="#323B55"
        ).pack(side="left", padx=6)

        create_button(
            buttons,
            "DOWNLOAD",
            lambda sid=schedule_id: download_qr_action(
                app,
                student,
                sid
            ),
            width=115,
            height=35,
            fg_color="#242B40",
            hover_color="#323B55"
        ).pack(side="left", padx=6)

        create_button(
            buttons,
            "PRINT",
            lambda sid=schedule_id: print_qr_action(
                app,
                student,
                sid
            ),
            width=95,
            height=35,
            fg_color="#242B40",
            hover_color="#323B55"
        ).pack(side="left", padx=6)

    # BIOMETRIC SECTION

    biometric = ctk.CTkFrame(
        main,
        fg_color=CARD,
        corner_radius=15,
        border_width=1,
        border_color=BORDER
    )
    biometric.pack(fill="x", pady=8)

    ctk.CTkLabel(
        biometric,
        text="BIOMETRIC VERIFICATION",
        font=("Arial", 17, "bold"),
        text_color=WHITE
    ).pack(anchor="w", padx=25, pady=(20, 5))

    ctk.CTkLabel(
        biometric,
        text="Face Recognition and Fingerprint registration will be added in the next stages.",
        font=("Arial", 11),
        text_color=MUTED
    ).pack(anchor="w", padx=25, pady=(0, 15))

    bio_buttons = ctk.CTkFrame(
        biometric,
        fg_color="transparent"
    )
    bio_buttons.pack(anchor="w", padx=25, pady=(0, 20))

    create_button(
        bio_buttons,
        "FACE REGISTER",
        lambda: face_register_action(student),
        width=180,
        fg_color="#242B40",
        hover_color="#323B55"
    ).pack(side="left", padx=(0, 10))

    create_button(
        bio_buttons,
        "FINGERPRINT REGISTER",
        lambda: fingerprint_register_action(
            student
        ),
        width=210,
        fg_color="#242B40",
        hover_color="#323B55"
    ).pack(side="left")


# ============================================================
# QR GENERATE
# ============================================================

def generate_qr_action(app, student, schedule_id):
    try:
        _, token, filename = create_qr_for_class(
            student[0],
            schedule_id
        )

        messagebox.showinfo(
            "QR Generated",
            "Your unique QR code has been generated successfully."
        )

        view_qr_window(
            app,
            student,
            schedule_id,
            filename,
            token
        )

    except Exception as error:
        messagebox.showerror(
            "QR Error",
            "Unable to generate QR code.\n\n" + str(error)
        )


# ============================================================
# GET QR INFORMATION
# ============================================================

def get_qr_information(student_id, schedule_id):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            qr_codes.token,
            qr_codes.qr_file,
            schedules.subject,
            teachers.name,
            schedules.course,
            schedules.year,
            schedules.section,
            schedules.day,
            schedules.start_time,
            schedules.end_time
        FROM qr_codes
        INNER JOIN schedules
            ON qr_codes.schedule_id = schedules.id
        INNER JOIN teachers
            ON schedules.teacher_id = teachers.id
        WHERE qr_codes.student_id = ?
          AND qr_codes.schedule_id = ?
    """, (
        student_id,
        schedule_id
    ))

    row = cursor.fetchone()
    connection.close()

    return row


# ============================================================
# VIEW QR
# ============================================================

def view_qr_action(app, student, schedule_id):
    information = get_qr_information(
        student[0],
        schedule_id
    )

    if not information:
        answer = messagebox.askyesno(
            "QR Not Generated",
            "QR code has not been generated for this class.\n\n"
            "Generate it now?"
        )

        if answer:
            generate_qr_action(
                app,
                student,
                schedule_id
            )

        return

    token = information[0]
    filename = information[1]

    if not filename or not os.path.exists(filename):
        try:
            _, token, filename = create_qr_for_class(
                student[0],
                schedule_id
            )
        except Exception as error:
            messagebox.showerror(
                "QR Error",
                str(error)
            )
            return

    view_qr_window(
        app,
        student,
        schedule_id,
        filename,
        token
    )


# ============================================================
# QR WINDOW
# ============================================================

def view_qr_window(app, student, schedule_id, filename, token):
    if not os.path.exists(filename):
        messagebox.showerror(
            "QR Error",
            "QR image file could not be found."
        )
        return

    information = get_qr_information(
        student[0],
        schedule_id
    )

    if not information:
        return

    window = ctk.CTkToplevel(app)
    window.title("ATTENDX | My QR Code")
    window.geometry("560x700")
    window.configure(fg_color=BG)
    window.resizable(False, False)

    window.transient(app)
    window.grab_set()

    ctk.CTkLabel(
        window,
        text="CLASS QR CODE",
        font=("Arial", 25, "bold"),
        text_color=WHITE
    ).pack(pady=(25, 5))

    ctk.CTkLabel(
        window,
        text=information[2],
        font=("Arial", 17, "bold"),
        text_color=PURPLE
    ).pack(pady=3)

    ctk.CTkLabel(
        window,
        text="Teacher: " + information[3],
        font=("Arial", 11),
        text_color=TEXT
    ).pack()

    ctk.CTkLabel(
        window,
        text=(
            information[4]
            + " | "
            + information[5]
            + " Year | Section "
            + information[6]
        ),
        font=("Arial", 10),
        text_color=MUTED
    ).pack(pady=3)

    try:
        image = Image.open(filename)
        image = image.resize((340, 340))

        qr_image = ctk.CTkImage(
            light_image=image,
            dark_image=image,
            size=(340, 340)
        )

        image_label = ctk.CTkLabel(
            window,
            text="",
            image=qr_image
        )
        image_label.pack(pady=20)

    except Exception as error:
        ctk.CTkLabel(
            window,
            text="Unable to display QR image.\n" + str(error),
            text_color=ERROR
        ).pack(pady=50)

    ctk.CTkLabel(
        window,
        text="QR TOKEN",
        font=("Arial", 10, "bold"),
        text_color=MUTED
    ).pack()

    token_label = ctk.CTkLabel(
        window,
        text=token,
        font=("Consolas", 9),
        text_color=TEXT
    )
    token_label.pack(pady=5)

    ctk.CTkLabel(
        window,
        text="Keep your QR code private.",
        font=("Arial", 10),
        text_color=WARNING
    ).pack(pady=5)

    create_button(
        window,
        "DOWNLOAD QR",
        lambda: download_qr_file(
            app,
            filename,
            information[2]
        ),
        width=180
    ).pack(pady=(10, 5))

    create_button(
        window,
        "PRINT QR",
        lambda: print_qr_file(
            filename
        ),
        width=180,
        fg_color="#242B40",
        hover_color="#323B55"
    ).pack(pady=5)

    create_button(
        window,
        "CLOSE",
        window.destroy,
        width=180,
        fg_color="#242B40",
        hover_color="#323B55"
    ).pack(pady=5)


# ============================================================
# DOWNLOAD QR
# ============================================================

def download_qr_action(app, student, schedule_id):
    information = get_qr_information(
        student[0],
        schedule_id
    )

    if not information:
        answer = messagebox.askyesno(
            "QR Not Generated",
            "Generate your QR code first?"
        )

        if answer:
            generate_qr_action(
                app,
                student,
                schedule_id
            )

        return

    filename = information[1]

    if not filename or not os.path.exists(filename):
        _, _, filename = create_qr_for_class(
            student[0],
            schedule_id
        )

    download_qr_file(
        app,
        filename,
        information[2]
    )


def download_qr_file(app, filename, subject):
    destination = filedialog.asksaveasfilename(
        parent=app,
        title="Save QR Code",
        initialfile="ATTENDX_" + subject.replace(" ", "_") + "_QR.png",
        defaultextension=".png",
        filetypes=[
            ("PNG Image", "*.png")
        ]
    )

    if not destination:
        return

    try:
        shutil.copy2(
            filename,
            destination
        )

        messagebox.showinfo(
            "Download Complete",
            "QR code saved successfully."
        )

    except Exception as error:
        messagebox.showerror(
            "Download Error",
            str(error)
        )


# ============================================================
# PRINT QR
# ============================================================

def print_qr_action(app, student, schedule_id):
    information = get_qr_information(
        student[0],
        schedule_id
    )

    if not information:
        messagebox.showwarning(
            "QR Not Ready",
            "Generate the QR code first."
        )
        return

    filename = information[1]

    if not filename or not os.path.exists(filename):
        messagebox.showerror(
            "Print Error",
            "QR image file does not exist."
        )
        return

    print_qr_file(filename)


def print_qr_file(filename):
    import platform
    import subprocess

    full_path = os.path.abspath(filename)

    try:
        system_name = platform.system()

        if system_name == "Windows":
            os.startfile(full_path, "print")

        elif system_name == "Darwin":
            subprocess.run(["lpr", full_path], check=True)

        else:
            subprocess.run(["lpr", full_path], check=True)

    except Exception as error:
        messagebox.showerror(
            "Print Error",
            "Could not send the QR image to the printer.\n\n"
            + str(error)
        )



def face_register_action(student):
    try:
        student_id = student[0]

        success = register_student_face(student_id)

        if success:
            messagebox.showinfo(
                "FACE REGISTRATION",
                "Face registration successful."
            )
        else:
            messagebox.showwarning(
                "FACE REGISTRATION",
                "Face registration was cancelled or could not be completed."
            )

    except Exception as error:
        messagebox.showerror(
            "FACE REGISTRATION ERROR",
            "Unable to register the student's face.`n`n"
            + str(error)
        )
# ============================================================
# BIOMETRIC PLACEHOLDER
# ============================================================

def biometric_coming_soon(title):
    messagebox.showinfo(
        title,
        title
        + " is prepared as part of the system design.\n\n"
          "This module will be connected in the next development stage."
    )


# ============================================================
# FINGERPRINT ACTIONS
# ============================================================

def teacher_portal(app):
    clear_screen(app)

    create_top_bar(
        app,
        app,
        True,
        lambda: role_selection(app)
    )

    create_page_title(
        app,
        "TEACHER PORTAL",
        "Manage schedules, students and attendance."
    )

    box = ctk.CTkFrame(
        app,
        width=500,
        height=360,
        fg_color=CARD,
        corner_radius=18,
        border_width=1,
        border_color=BORDER
    )
    box.pack(expand=True)
    box.pack_propagate(False)

    ctk.CTkLabel(
        box,
        text="Teacher Account",
        font=("Arial", 23, "bold"),
        text_color=WHITE
    ).pack(pady=(35, 20))

    create_button(
        box,
        "CREATE ACCOUNT",
        lambda: teacher_register_page(app),
        width=300
    ).pack(pady=8)

    create_button(
        box,
        "LOG IN",
        lambda: teacher_login_page(app),
        width=300
    ).pack(pady=8)


# ============================================================
# TEACHER REGISTER
# ============================================================

def teacher_forgot_password(app):
    clear_screen(app)

    create_top_bar(
        app,
        app,
        True,
        lambda: teacher_login_page(app)
    )

    create_page_title(
        app,
        "FORGOT PASSWORD",
        "Reset your teacher account password."
    )

    form = ctk.CTkFrame(
        app,
        width=500,
        height=390,
        fg_color=CARD,
        corner_radius=18,
        border_width=1,
        border_color=BORDER
    )
    form.pack(expand=True)
    form.pack_propagate(False)

    teacher_id = create_input(form, "Teacher ID")
    new_password = create_input(form, "New Password", show="*")
    confirm = create_input(form, "Confirm New Password", show="*")

    def reset():
        tid = teacher_id.get().strip()
        new_pass = new_password.get()
        confirm_pass = confirm.get()

        if not tid or not new_pass or not confirm_pass:
            messagebox.showerror(
                "Error",
                "Please complete all fields."
            )
            return

        if len(new_pass) < 6:
            messagebox.showerror(
                "Error",
                "Password must contain at least 6 characters."
            )
            return

        if new_pass != confirm_pass:
            messagebox.showerror(
                "Error",
                "Passwords do not match."
            )
            return

        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            "SELECT id FROM teachers WHERE teacher_id = ?",
            (tid,)
        )

        teacher = cursor.fetchone()

        if not teacher:
            connection.close()

            messagebox.showerror(
                "Error",
                "Teacher ID does not exist."
            )
            return

        cursor.execute("""
            UPDATE teachers
            SET password = ?
            WHERE teacher_id = ?
        """, (
            hash_password(new_pass),
            tid
        ))

        connection.commit()
        connection.close()

        messagebox.showinfo(
            "Password Updated",
            "Your password has been successfully changed."
        )

        teacher_login_page(app)

    create_button(
        form,
        "RESET PASSWORD",
        reset,
        width=300
    ).pack(pady=30)


# ============================================================
# TIME CONVERSION
# ============================================================

def convert_time(value):
    try:
        hour, minute = value.split(":")

        hour = int(hour)
        minute = int(minute)

        if hour < 0 or hour > 23:
            return None

        if minute < 0 or minute > 59:
            return None

        return hour * 60 + minute

    except Exception:
        return None


# ============================================================
# 12-HOUR TIME HELPERS
#
# Schedules are always stored in the database as 24-hour
# "HH:MM" text (so sorting and comparisons stay simple), but
# people think and type in 12-hour AM/PM time. These helpers
# convert between the two so the UI can use plain, unambiguous
# Hour / Minute / AM-PM pickers instead of a free-text box.
# ============================================================

def to_24_hour(hour_12, minute, period):
    try:
        hour_12 = int(hour_12)
    except Exception:
        hour_12 = 12

    period = (period or "AM").strip().upper()

    if period == "AM":
        hour_24 = 0 if hour_12 == 12 else hour_12
    else:
        hour_24 = 12 if hour_12 == 12 else hour_12 + 12

    return "{:02d}:{}".format(hour_24, minute)


def format_time_12h(time_value):
    try:
        hour, minute = time_value.split(":")
        hour = int(hour)

        period = "AM" if hour < 12 else "PM"

        hour_12 = hour % 12
        if hour_12 == 0:
            hour_12 = 12

        return "{}:{} {}".format(hour_12, minute, period)

    except Exception:
        return time_value


def create_time_selector(parent, label_text, default_hour="7",
                          default_minute="00", default_period="AM"):
    wrapper = ctk.CTkFrame(parent, fg_color="transparent")
    wrapper.pack(fill="x", pady=6)

    ctk.CTkLabel(
        wrapper,
        text=label_text,
        font=("Arial", 11, "bold"),
        text_color=MUTED
    ).pack(anchor="w", pady=(0, 4))

    row = ctk.CTkFrame(wrapper, fg_color="transparent")
    row.pack(fill="x")

    hour_box = ctk.CTkComboBox(
        row,
        values=[str(h) for h in range(1, 13)],
        width=90,
        height=44,
        corner_radius=8,
        fg_color=CARD_2,
        border_color=BORDER,
        button_color=PURPLE,
        button_hover_color=PURPLE_HOVER,
        text_color=WHITE
    )
    hour_box.set(default_hour)
    hour_box.pack(side="left", padx=(0, 8))

    ctk.CTkLabel(
        row,
        text=":",
        font=("Arial", 16, "bold"),
        text_color=WHITE
    ).pack(side="left")

    minute_box = ctk.CTkComboBox(
        row,
        values=["00", "15", "30", "45"],
        width=90,
        height=44,
        corner_radius=8,
        fg_color=CARD_2,
        border_color=BORDER,
        button_color=PURPLE,
        button_hover_color=PURPLE_HOVER,
        text_color=WHITE
    )
    minute_box.set(default_minute)
    minute_box.pack(side="left", padx=8)

    period_box = ctk.CTkComboBox(
        row,
        values=["AM", "PM"],
        width=100,
        height=44,
        corner_radius=8,
        fg_color=CARD_2,
        border_color=BORDER,
        button_color=PURPLE,
        button_hover_color=PURPLE_HOVER,
        text_color=WHITE
    )
    period_box.set(default_period)
    period_box.pack(side="left", padx=8)

    return wrapper, hour_box, minute_box, period_box


# ============================================================
# TEACHER ADD SCHEDULE
# ============================================================

def teacher_add_subject_page(app, teacher):
    """Design companion for Add Subject; keeps the original schedule flow."""
    clear_screen(app)
    create_top_bar(
        app, app, True,
        lambda: teacher_dashboard(app, teacher)
    )
    create_page_title(
        app,
        "ADD SUBJECT",
        "Create a subject by adding its class schedule details."
    )

    card = ctk.CTkFrame(
        app, width=760, height=390, fg_color=CARD,
        corner_radius=18, border_width=1, border_color=BORDER
    )
    card.pack(expand=True)
    card.pack_propagate(False)

    ctk.CTkLabel(
        card, text="SUBJECT SETUP", font=("Arial", 22, "bold"),
        text_color=WHITE
    ).pack(pady=(30, 6))
    ctk.CTkLabel(
        card,
        text="The existing Add Schedule form is used so the original flow stays unchanged.",
        font=("Arial", 11), text_color=MUTED
    ).pack(pady=(0, 20))

    create_button(
        card, "CONTINUE TO ADD SCHEDULE",
        lambda: teacher_add_schedule_page(app, teacher), width=320
    ).pack(pady=10)
    create_button(
        card, "BACK TO DASHBOARD",
        lambda: teacher_dashboard(app, teacher), width=320,
        fg_color="#242B40", hover_color="#323B55"
    ).pack(pady=8)


# ============================================================
# TEACHER MY SCHEDULE
# ============================================================

def teacher_my_schedule_page(app, teacher):
    clear_screen(app)

    create_top_bar(
        app,
        app,
        True,
        lambda: teacher_dashboard(app, teacher)
    )

    create_page_title(
        app,
        "MY SCHEDULE",
        "All schedules created by your teacher account."
    )

    container = ctk.CTkScrollableFrame(
        app,
        fg_color="transparent"
    )
    container.pack(fill="both", expand=True, padx=55, pady=10)

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            course,
            subject,
            section,
            year,
            day,
            start_time,
            end_time
        FROM schedules
        WHERE teacher_id = ?
        ORDER BY
            CASE day
                WHEN 'Monday' THEN 1
                WHEN 'Tuesday' THEN 2
                WHEN 'Wednesday' THEN 3
                WHEN 'Thursday' THEN 4
                WHEN 'Friday' THEN 5
            END,
            start_time
    """, (teacher[0],))

    schedules = cursor.fetchall()
    connection.close()

    if not schedules:
        ctk.CTkLabel(
            container,
            text="No schedules created yet.",
            font=("Arial", 15),
            text_color=MUTED
        ).pack(pady=60)
        return

    for item in schedules:
        card = ctk.CTkFrame(
            container,
            fg_color=CARD,
            corner_radius=14,
            border_width=1,
            border_color=BORDER
        )
        card.pack(fill="x", pady=6)

        ctk.CTkLabel(
            card,
            text=item[2],
            font=("Arial", 19, "bold"),
            text_color=WHITE
        ).pack(anchor="w", padx=20, pady=(15, 4))

        ctk.CTkLabel(
            card,
            text=(
                "Course: "
                + item[1]
                + " | Year: "
                + item[4]
                + " | Section: "
                + item[3]
            ),
            font=("Arial", 11),
            text_color=TEXT
        ).pack(anchor="w", padx=20)

        ctk.CTkLabel(
            card,
            text=(
                item[5]
                + "  "
                + format_time_12h(item[6])
                + " - "
                + format_time_12h(item[7])
            ),
            font=("Arial", 11),
            text_color=MUTED
        ).pack(anchor="w", padx=20, pady=(4, 15))


# ============================================================
# TEACHER MY STUDENTS
# ============================================================

def teacher_delete_student_from_classes(app, teacher, student_id, student_name):
    answer = messagebox.askyesno(
        "REMOVE STUDENT",
        "Remove " + str(student_name) + " from your class/classes?\n\n"
        "The student's account will NOT be deleted.\n"
        "Only this student's enrollment under your classes will be removed."
    )

    if not answer:
        return

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            DELETE FROM student_classes
            WHERE student_id = ?
              AND schedule_id IN (
                  SELECT id
                  FROM schedules
                  WHERE teacher_id = ?
              )
        """, (student_id, teacher[0]))

        removed_count = cursor.rowcount
        connection.commit()

        if removed_count > 0:
            messagebox.showinfo(
                "REMOVE STUDENT",
                str(student_name) + " was removed from your class."
            )
        else:
            messagebox.showwarning(
                "REMOVE STUDENT",
                "No class enrollment was found for this student."
            )

    except Exception as error:
        connection.rollback()
        messagebox.showerror(
            "REMOVE STUDENT",
            "Unable to remove student.\n\n" + str(error)
        )

    finally:
        connection.close()

    teacher_my_students_page(app, teacher)


def teacher_student_attendance_reference(app, teacher, student_id, student_name):
    clear_screen(app)

    create_top_bar(
        app,
        app,
        True,
        lambda: teacher_my_students_page(app, teacher)
    )

    create_page_title(
        app,
        "STUDENT ATTENDANCE",
        "Attendance reference for " + str(student_name) + "."
    )

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            schedules.subject,
            schedules.day,
            schedules.start_time,
            schedules.end_time,
            attendance.attendance_date,
            attendance.attendance_time,
            attendance.status,
            attendance.method
        FROM student_classes
        INNER JOIN schedules
            ON student_classes.schedule_id = schedules.id
        LEFT JOIN attendance
            ON attendance.student_id = student_classes.student_id
            AND attendance.schedule_id = schedules.id
        WHERE student_classes.student_id = ?
          AND schedules.teacher_id = ?
        ORDER BY
            attendance.attendance_date DESC,
            schedules.day,
            schedules.start_time,
            schedules.subject
    """, (student_id, teacher[0]))

    records = cursor.fetchall()
    connection.close()

    header = ctk.CTkFrame(
        app,
        fg_color=CARD,
        corner_radius=12,
        border_width=1,
        border_color=BORDER
    )
    header.pack(fill="x", padx=55, pady=(5, 8))

    ctk.CTkLabel(
        header,
        text="Student: " + str(student_name),
        font=("Arial", 16, "bold"),
        text_color=WHITE
    ).pack(anchor="w", padx=18, pady=(12, 3))

    ctk.CTkLabel(
        header,
        text="Records shown only for classes handled by this TC.",
        font=("Arial", 10),
        text_color=MUTED
    ).pack(anchor="w", padx=18, pady=(0, 12))

    container = ctk.CTkScrollableFrame(
        app,
        fg_color="transparent"
    )
    container.pack(fill="both", expand=True, padx=55, pady=5)

    if not records:
        ctk.CTkLabel(
            container,
            text="No attendance records found.",
            font=("Arial", 15),
            text_color=MUTED
        ).pack(pady=60)
        return

    for record in records:
        subject, day, start_time, end_time, attendance_date, attendance_time, status, method = record

        status_text = status if status else "NO RECORD"
        method_text = method if method else "-"
        date_text = attendance_date if attendance_date else "No attendance date"
        time_text = attendance_time if attendance_time else "-"

        card = ctk.CTkFrame(
            container,
            fg_color=CARD,
            corner_radius=12,
            border_width=1,
            border_color=BORDER
        )
        card.pack(fill="x", pady=5)

        ctk.CTkLabel(
            card,
            text=str(subject),
            font=("Arial", 15, "bold"),
            text_color=WHITE
        ).pack(anchor="w", padx=18, pady=(12, 2))

        ctk.CTkLabel(
            card,
            text=(
                str(day)
                + " | "
                + format_time_12h(start_time)
                + " - "
                + format_time_12h(end_time)
            ),
            font=("Arial", 10),
            text_color=MUTED
        ).pack(anchor="w", padx=18, pady=2)

        stats_row = ctk.CTkFrame(card, fg_color="transparent")
        stats_row.pack(fill="x", padx=12, pady=(4, 12))

        ctk.CTkLabel(
            stats_row,
            text="DATE\n" + date_text,
            width=180,
            height=45,
            corner_radius=8,
            fg_color=CARD_2,
            text_color=TEXT,
            font=("Arial", 10, "bold")
        ).pack(side="left", padx=5)

        ctk.CTkLabel(
            stats_row,
            text="TIME\n" + time_text,
            width=130,
            height=45,
            corner_radius=8,
            fg_color=CARD_2,
            text_color=TEXT,
            font=("Arial", 10, "bold")
        ).pack(side="left", padx=5)

        ctk.CTkLabel(
            stats_row,
            text="STATUS\n" + status_text,
            width=130,
            height=45,
            corner_radius=8,
            fg_color=CARD_2,
            text_color=SUCCESS if status_text == "PRESENT" else WARNING if status_text == "LATE" else ERROR if status_text == "ABSENT" else MUTED,
            font=("Arial", 10, "bold")
        ).pack(side="left", padx=5)

        ctk.CTkLabel(
            stats_row,
            text="METHOD\n" + method_text,
            width=130,
            height=45,
            corner_radius=8,
            fg_color=CARD_2,
            text_color=PURPLE,
            font=("Arial", 10, "bold")
        ).pack(side="left", padx=5)


def teacher_my_students_page(app, teacher):
    clear_screen(app)

    create_top_bar(
        app,
        app,
        True,
        lambda: teacher_dashboard(app, teacher)
    )

    create_page_title(
        app,
        "MY STUDENTS",
        "Students matched to your classes with attendance totals."
    )

    container = ctk.CTkScrollableFrame(
        app,
        fg_color="transparent"
    )
    container.pack(fill="both", expand=True, padx=55, pady=10)

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT DISTINCT
            students.id,
            students.school_id,
            students.name,
            students.course,
            students.year,
            students.section
        FROM student_classes
        INNER JOIN students
            ON student_classes.student_id = students.id
        INNER JOIN schedules
            ON student_classes.schedule_id = schedules.id
        WHERE schedules.teacher_id = ?
        ORDER BY students.name
    """, (teacher[0],))

    students = cursor.fetchall()

    if not students:
        connection.close()
        ctk.CTkLabel(
            container,
            text="No students have been matched to your classes yet.",
            font=("Arial", 15),
            text_color=MUTED
        ).pack(pady=60)
        return

    for student in students:
        student_id, school_id, student_name, course, year, section = student

        cursor.execute("""
            SELECT COUNT(*)
            FROM student_classes
            INNER JOIN schedules
                ON student_classes.schedule_id = schedules.id
            WHERE student_classes.student_id = ?
              AND schedules.teacher_id = ?
        """, (student_id, teacher[0]))
        class_count = cursor.fetchone()[0]

        cursor.execute("""
            SELECT
                SUM(CASE WHEN attendance.status = 'PRESENT' THEN 1 ELSE 0 END),
                SUM(CASE WHEN attendance.status = 'LATE' THEN 1 ELSE 0 END),
                SUM(CASE WHEN attendance.status = 'ABSENT' THEN 1 ELSE 0 END)
            FROM attendance
            INNER JOIN schedules
                ON attendance.schedule_id = schedules.id
            WHERE attendance.student_id = ?
              AND schedules.teacher_id = ?
        """, (student_id, teacher[0]))

        totals = cursor.fetchone()
        present_count = totals[0] or 0
        late_count = totals[1] or 0
        absent_count = totals[2] or 0

        card = ctk.CTkFrame(
            container,
            fg_color=CARD,
            corner_radius=14,
            border_width=1,
            border_color=BORDER
        )
        card.pack(fill="x", pady=7)

        top_row = ctk.CTkFrame(card, fg_color="transparent")
        top_row.pack(fill="x", padx=20, pady=(15, 5))

        ctk.CTkLabel(
            top_row,
            text=student_name,
            font=("Arial", 17, "bold"),
            text_color=WHITE
        ).pack(side="left")

        ctk.CTkLabel(
            top_row,
            text=str(class_count) + " class" + ("es" if class_count != 1 else ""),
            font=("Arial", 10, "bold"),
            text_color=PURPLE
        ).pack(side="right")

        ctk.CTkLabel(
            card,
            text="School ID: " + str(school_id),
            font=("Arial", 10),
            text_color=MUTED
        ).pack(anchor="w", padx=20)

        ctk.CTkLabel(
            card,
            text=(
                str(course)
                + " | "
                + str(year)
                + " Year | Section "
                + str(section)
            ),
            font=("Arial", 11),
            text_color=TEXT
        ).pack(anchor="w", padx=20, pady=(3, 7))

        stats_row = ctk.CTkFrame(card, fg_color="transparent")
        stats_row.pack(fill="x", padx=15, pady=(0, 8))

        def stat_box(parent, title, value, text_color):
            box = ctk.CTkFrame(
                parent,
                fg_color=CARD_2,
                corner_radius=10,
                border_width=1,
                border_color=BORDER
            )
            box.pack(side="left", fill="x", expand=True, padx=5)

            ctk.CTkLabel(
                box,
                text=str(value),
                font=("Arial", 18, "bold"),
                text_color=text_color
            ).pack(pady=(8, 0))

            ctk.CTkLabel(
                box,
                text=title,
                font=("Arial", 9, "bold"),
                text_color=MUTED
            ).pack(pady=(0, 8))

        stat_box(stats_row, "PRESENT", present_count, SUCCESS)
        stat_box(stats_row, "LATE", late_count, WARNING)
        stat_box(stats_row, "ABSENT", absent_count, ERROR)

        buttons = ctk.CTkFrame(card, fg_color="transparent")
        buttons.pack(fill="x", padx=15, pady=(2, 15))

        create_button(
            buttons,
            "VIEW ATTENDANCE",
            lambda sid=student_id, name=student_name: teacher_student_attendance_reference(
                app,
                teacher,
                sid,
                name
            ),
            width=180
        ).pack(side="left", padx=5)

        create_button(
            buttons,
            "REMOVE STUDENT",
            lambda sid=student_id, name=student_name: teacher_delete_student_from_classes(
                app,
                teacher,
                sid,
                name
            ),
            width=180
        ).pack(side="left", padx=5)

    connection.close()


# ============================================================
# ATTENDANCE STATUS
# ============================================================

def teacher_attendance_page(app, teacher):
    clear_screen(app)

    create_top_bar(
        app,
        app,
        True,
        lambda: teacher_dashboard(app, teacher)
    )

    create_page_title(
        app,
        "ATTENDANCE",
        "Select a class and choose a verification method."
    )

    form = ctk.CTkFrame(
        app,
        width=700,
        height=500,
        fg_color=CARD,
        corner_radius=18,
        border_width=1,
        border_color=BORDER
    )
    form.pack(expand=True)
    form.pack_propagate(False)

    ctk.CTkLabel(
        form,
        text="START ATTENDANCE",
        font=("Arial", 23, "bold"),
        text_color=WHITE
    ).pack(pady=(30, 10))

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            schedules.id,
            schedules.subject,
            schedules.course,
            schedules.year,
            schedules.section,
            schedules.day,
            schedules.start_time,
            schedules.end_time
        FROM schedules
        WHERE schedules.teacher_id = ?
        ORDER BY schedules.day, schedules.start_time
    """, (teacher[0],))

    schedules = cursor.fetchall()
    connection.close()

    schedule_values = []
    schedule_lookup = {}

    for item in schedules:
        text = (
            str(item[0])
            + " | "
            + item[1]
            + " | "
            + item[2]
            + " | "
            + item[3]
            + " | Section "
            + item[4]
            + " | "
            + item[5]
            + " "
            + format_time_12h(item[6])
            + "-"
            + format_time_12h(item[7])
        )

        schedule_values.append(text)
        schedule_lookup[text] = item

    if not schedule_values:
        ctk.CTkLabel(
            form,
            text="No schedules available.",
            font=("Arial", 13),
            text_color=WARNING
        ).pack(pady=40)
        return

    schedule_box = ctk.CTkComboBox(
        form,
        values=schedule_values,
        width=600,
        height=45,
        corner_radius=8,
        fg_color=CARD_2,
        border_color=BORDER,
        button_color=PURPLE,
        button_hover_color=PURPLE_HOVER,
        text_color=WHITE
    )
    schedule_box.set(schedule_values[0])
    schedule_box.pack(pady=15)

    method_box = ctk.CTkComboBox(
        form,
        values=[
            "SCAN QR",
            "FACE",
            "FINGERPRINT"
        ],
        width=600,
        height=45,
        corner_radius=8,
        fg_color=CARD_2,
        border_color=BORDER,
        button_color=PURPLE,
        button_hover_color=PURPLE_HOVER,
        text_color=WHITE
    )
    method_box.set("SCAN QR")
    method_box.pack(pady=10)

    ctk.CTkLabel(
        form,
        text=(
            "QR verification is the current active verification method.\n"
            "Face and Fingerprint will be connected in later stages."
        ),
        font=("Arial", 11),
        text_color=MUTED,
        justify="center"
    ).pack(pady=15)

    def start_attendance():
        method = method_box.get()

        if method == "SCAN QR":
            selected_text = schedule_box.get()
            selected_row = schedule_lookup.get(selected_text)

            if not selected_row:
                messagebox.showerror(
                    "Error",
                    "Please choose a class from the list."
                )
                return

            attendance_qr_page(
                app,
                teacher,
                selected_row
            )

        elif method == "FACE":
            selected_text = schedule_box.get()
            selected_row = schedule_lookup.get(selected_text)

            if not selected_row:
                messagebox.showerror(
                    "Error",
                    "Please choose a class from the list."
                )
                return

            face_attendance_action(
                app,
                teacher,
                selected_row
            )

        else:
            selected_text = schedule_box.get()
            selected_row = schedule_lookup.get(selected_text)

            if not selected_row:
                messagebox.showerror(
                    "Error",
                    "Please choose a class from the list."
                )
                return

            fingerprint_attendance_action(
                app,
                teacher,
                selected_row
            )

    create_button(
        form,
        "START ATTENDANCE",
        start_attendance,
        width=280
    ).pack(pady=20)


# ============================================================
# QR ATTENDANCE
# ============================================================

def teacher_attendance_records_page(app, teacher):
    clear_screen(app)

    create_top_bar(
        app,
        app,
        True,
        lambda: teacher_dashboard(app, teacher)
    )

    create_page_title(
        app,
        "ATTENDANCE RECORDS",
        "View attendance records from your classes."
    )

    container = ctk.CTkScrollableFrame(
        app,
        fg_color="transparent"
    )
    container.pack(
        fill="both",
        expand=True,
        padx=55,
        pady=10
    )

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            attendance.attendance_date,
            attendance.attendance_time,
            attendance.status,
            attendance.method,
            students.school_id,
            students.name,
            students.course,
            students.year,
            students.section,
            schedules.subject,
            schedules.day,
            schedules.start_time,
            schedules.end_time
        FROM attendance
        INNER JOIN students
            ON attendance.student_id = students.id
        INNER JOIN schedules
            ON attendance.schedule_id = schedules.id
        WHERE schedules.teacher_id = ?
        ORDER BY
            attendance.attendance_date DESC,
            attendance.attendance_time DESC
    """, (teacher[0],))

    records = cursor.fetchall()
    connection.close()

    if not records:
        empty = ctk.CTkFrame(
            container,
            fg_color=CARD,
            corner_radius=15,
            border_width=1,
            border_color=BORDER
        )
        empty.pack(fill="x", pady=20)

        ctk.CTkLabel(
            empty,
            text="NO ATTENDANCE RECORDS",
            font=("Arial", 20, "bold"),
            text_color=WHITE
        ).pack(pady=(50, 10))

        ctk.CTkLabel(
            empty,
            text="Verified student attendance will appear here.",
            font=("Arial", 12),
            text_color=MUTED
        ).pack(pady=(0, 50))

        return

    for record in records:
        card = ctk.CTkFrame(
            container,
            fg_color=CARD,
            corner_radius=14,
            border_width=1,
            border_color=BORDER
        )
        card.pack(fill="x", pady=6)

        top = ctk.CTkFrame(
            card,
            fg_color="transparent"
        )
        top.pack(
            fill="x",
            padx=20,
            pady=(15, 5)
        )

        ctk.CTkLabel(
            top,
            text=record[5],
            font=("Arial", 17, "bold"),
            text_color=WHITE
        ).pack(side="left")

        status_color = SUCCESS

        if record[2] == "LATE":
            status_color = WARNING
        elif record[2] == "ABSENT":
            status_color = ERROR

        ctk.CTkLabel(
            top,
            text=record[2],
            font=("Arial", 11, "bold"),
            text_color=status_color
        ).pack(side="right")

        ctk.CTkLabel(
            card,
            text="School ID: " + record[4],
            font=("Arial", 10),
            text_color=MUTED
        ).pack(
            anchor="w",
            padx=20
        )

        ctk.CTkLabel(
            card,
            text=(
                record[6]
                + " | "
                + record[7]
                + " Year | Section "
                + record[8]
            ),
            font=("Arial", 11),
            text_color=TEXT
        ).pack(
            anchor="w",
            padx=20,
            pady=3
        )

        ctk.CTkLabel(
            card,
            text=(
                "Subject: "
                + record[9]
                + " | "
                + record[10]
                + " "
                + format_time_12h(record[11])
                + "-"
                + format_time_12h(record[12])
            ),
            font=("Arial", 11),
            text_color=PURPLE
        ).pack(
            anchor="w",
            padx=20,
            pady=3
        )

        ctk.CTkLabel(
            card,
            text=(
                "Date: "
                + record[0]
                + " | Time: "
                + record[1]
                + " | Method: "
                + record[3]
            ),
            font=("Arial", 10),
            text_color=MUTED
        ).pack(
            anchor="w",
            padx=20,
            pady=(3, 15)
        )


# ============================================================
# TEACHER DASHBOARD ATTENDANCE BUTTON UPDATE
# ============================================================

def teacher_attendance_menu_page(app, teacher):
    clear_screen(app)

    create_top_bar(
        app,
        app,
        True,
        lambda: teacher_dashboard(app, teacher)
    )

    create_page_title(
        app,
        "ATTENDANCE CENTER",
        "Start attendance verification or view attendance records."
    )

    box = ctk.CTkFrame(
        app,
        width=650,
        height=400,
        fg_color=CARD,
        corner_radius=18,
        border_width=1,
        border_color=BORDER
    )
    box.pack(expand=True)
    box.pack_propagate(False)

    ctk.CTkLabel(
        box,
        text="ATTENDANCE CENTER",
        font=("Arial", 23, "bold"),
        text_color=WHITE
    ).pack(pady=(35, 20))

    create_button(
        box,
        "START ATTENDANCE",
        lambda: teacher_attendance_page(app, teacher),
        width=300
    ).pack(pady=8)

    create_button(
        box,
        "VIEW ATTENDANCE RECORDS",
        lambda: teacher_attendance_records_page(app, teacher),
        width=300
    ).pack(pady=8)

    create_button(
        box,
        "BACK TO DASHBOARD",
        lambda: teacher_dashboard(app, teacher),
        width=300,
        fg_color="#242B40",
        hover_color="#323B55"
    ).pack(pady=8)


# ============================================================
# TEACHER DASHBOARD HELPERS
# ============================================================

def get_teacher_dashboard_data(teacher_id):
    """Get attendance summaries and today's schedule for one teacher."""
    connection = get_connection()
    cursor = connection.cursor()

    today = datetime.now()
    today_date = today.strftime("%Y-%m-%d")
    today_day = today.strftime("%A")

    # Current week: Monday through Sunday.
    week_start = (today - __import__("datetime").timedelta(days=today.weekday())).strftime("%Y-%m-%d")
    week_end = (today + __import__("datetime").timedelta(days=6 - today.weekday())).strftime("%Y-%m-%d")

    month_start = today.strftime("%Y-%m-01")
    month_end = (today.replace(day=28) + __import__("datetime").timedelta(days=4)).replace(day=1)
    month_end = (month_end - __import__("datetime").timedelta(days=1)).strftime("%Y-%m-%d")

    def attendance_summary(start_date, end_date):
        cursor.execute("""
            SELECT
                COUNT(*),
                SUM(CASE WHEN attendance.status = 'PRESENT' THEN 1 ELSE 0 END),
                SUM(CASE WHEN attendance.status = 'LATE' THEN 1 ELSE 0 END),
                SUM(CASE WHEN attendance.status = 'ABSENT' THEN 1 ELSE 0 END)
            FROM attendance
            INNER JOIN schedules
                ON attendance.schedule_id = schedules.id
            WHERE schedules.teacher_id = ?
              AND attendance.attendance_date BETWEEN ? AND ?
        """, (teacher_id, start_date, end_date))

        row = cursor.fetchone()
        return (
            int(row[0] or 0),
            int(row[1] or 0),
            int(row[2] or 0),
            int(row[3] or 0)
        )

    daily = attendance_summary(today_date, today_date)
    weekly = attendance_summary(week_start, week_end)
    monthly = attendance_summary(month_start, month_end)

    cursor.execute("""
        SELECT
            schedules.id,
            schedules.subject,
            schedules.course,
            schedules.year,
            schedules.section,
            schedules.start_time,
            schedules.end_time,
            (
                SELECT COUNT(*)
                FROM student_classes
                WHERE student_classes.schedule_id = schedules.id
            )
        FROM schedules
        WHERE schedules.teacher_id = ?
          AND schedules.day = ?
        ORDER BY schedules.start_time
    """, (teacher_id, today_day))

    today_schedules = cursor.fetchall()

    cursor.execute("""
        SELECT
            schedules.day,
            schedules.subject,
            schedules.course,
            schedules.year,
            schedules.section,
            schedules.start_time,
            schedules.end_time,
            (
                SELECT COUNT(*)
                FROM student_classes
                WHERE student_classes.schedule_id = schedules.id
            )
        FROM schedules
        WHERE schedules.teacher_id = ?
        ORDER BY
            CASE schedules.day
                WHEN 'Monday' THEN 1
                WHEN 'Tuesday' THEN 2
                WHEN 'Wednesday' THEN 3
                WHEN 'Thursday' THEN 4
                WHEN 'Friday' THEN 5
                ELSE 6
            END,
            schedules.start_time
    """, (teacher_id,))

    weekly_schedules = cursor.fetchall()

    connection.close()

    return {
        "today_date": today_date,
        "today_day": today_day,
        "week_start": week_start,
        "week_end": week_end,
        "month_start": month_start,
        "month_end": month_end,
        "daily": daily,
        "weekly": weekly,
        "monthly": monthly,
        "today_schedules": today_schedules,
        "weekly_schedules": weekly_schedules
    }


def create_dashboard_stat_card(parent, title, value, color=WHITE):
    card = ctk.CTkFrame(
        parent,
        fg_color=CARD,
        corner_radius=14,
        border_width=1,
        border_color=BORDER
    )
    card.pack(side="left", fill="both", expand=True, padx=5)

    ctk.CTkLabel(
        card,
        text=title,
        font=("Arial", 10, "bold"),
        text_color=MUTED
    ).pack(pady=(14, 2))

    ctk.CTkLabel(
        card,
        text=str(value),
        font=("Arial", 25, "bold"),
        text_color=color
    ).pack(pady=(0, 14))

    return card


def create_dashboard_schedule_card(parent, item, show_day=False):
    card = ctk.CTkFrame(
        parent,
        fg_color=CARD,
        corner_radius=12,
        border_width=1,
        border_color=BORDER
    )
    card.pack(fill="x", pady=5)

    left = ctk.CTkFrame(card, fg_color="transparent")
    left.pack(side="left", fill="both", expand=True, padx=18, pady=12)

    if show_day:
        ctk.CTkLabel(
            left,
            text=item[0].upper(),
            font=("Arial", 10, "bold"),
            text_color=PURPLE
        ).pack(anchor="w")

        subject = item[1]
        course = item[2]
        year = item[3]
        section = item[4]
        start_time = item[5]
        end_time = item[6]
        student_count = item[7]
    else:
        subject = item[1]
        course = item[2]
        year = item[3]
        section = item[4]
        start_time = item[5]
        end_time = item[6]
        student_count = item[7]

    ctk.CTkLabel(
        left,
        text=subject,
        font=("Arial", 16, "bold"),
        text_color=WHITE
    ).pack(anchor="w", pady=(2, 2))

    ctk.CTkLabel(
        left,
        text=(
            course + "  •  " + year + " Year  •  Section " + section
        ),
        font=("Arial", 10),
        text_color=TEXT
    ).pack(anchor="w")

    ctk.CTkLabel(
        left,
        text=str(student_count) + " registered student/s",
        font=("Arial", 10),
        text_color=MUTED
    ).pack(anchor="w", pady=(3, 0))

    ctk.CTkLabel(
        card,
        text=(
            format_time_12h(start_time)
            + "\n"
            + format_time_12h(end_time)
        ),
        font=("Arial", 11, "bold"),
        text_color=PURPLE,
        justify="right"
    ).pack(side="right", padx=18, pady=12)

    return card


# ============================================================
# UPDATED TEACHER DASHBOARD
# ============================================================

def teacher_dashboard(app, teacher):
    """AttendX TC/Teacher dashboard - A+C inspired sidebar layout with visible animations."""
    clear_screen(app)

    data = get_teacher_dashboard_data(teacher[0])

    # ========================================================
    # A+C STYLE DASHBOARD SHELL
    # ========================================================
    shell = ctk.CTkFrame(app, fg_color=BG, corner_radius=0)
    shell.pack(fill="both", expand=True)

    # --------------------------------------------------------
    # LEFT SIDEBAR
    # --------------------------------------------------------
    sidebar = ctk.CTkFrame(
        shell,
        width=235,
        fg_color=CARD,
        corner_radius=0,
        border_width=1,
        border_color=BORDER
    )
    sidebar.pack(side="left", fill="y")
    sidebar.pack_propagate(False)

    brand = ctk.CTkFrame(sidebar, fg_color="transparent")
    brand.pack(fill="x", padx=20, pady=(24, 18))

    brand_mark = ctk.CTkLabel(
        brand,
        text="A",
        width=43,
        height=43,
        corner_radius=13,
        fg_color=PURPLE,
        text_color=WHITE,
        font=("Arial", 22, "bold")
    )
    brand_mark.pack(side="left")

    brand_text = ctk.CTkFrame(brand, fg_color="transparent")
    brand_text.pack(side="left", padx=10)

    ctk.CTkLabel(
        brand_text,
        text="ATTENDX",
        font=("Arial", 17, "bold"),
        text_color=WHITE
    ).pack(anchor="w")
    ctk.CTkLabel(
        brand_text,
        text="TC CONTROL CENTER",
        font=("Arial", 8, "bold"),
        text_color=MUTED
    ).pack(anchor="w")

    ctk.CTkFrame(sidebar, height=1, fg_color=BORDER).pack(fill="x", padx=18, pady=(0, 15))

    ctk.CTkLabel(
        sidebar,
        text="WORKSPACE",
        font=("Arial", 9, "bold"),
        text_color=MUTED
    ).pack(anchor="w", padx=23, pady=(0, 8))

    # Sidebar button helper with hover animation.
    def side_button(text, command, active=False):
        holder = ctk.CTkFrame(sidebar, height=44, fg_color="transparent", corner_radius=10)
        holder.pack(fill="x", padx=12, pady=3)
        holder.pack_propagate(False)

        button = ctk.CTkButton(
            holder,
            text="  " + text,
            command=command,
            height=44,
            corner_radius=10,
            anchor="w",
            font=("Arial", 11, "bold"),
            fg_color=PURPLE if active else "transparent",
            hover_color=PURPLE_HOVER if active else CARD_2,
            text_color=WHITE if active else TEXT
        )
        button.pack(fill="both", expand=True)

        def enter(_=None):
            if not active:
                button.configure(fg_color=CARD_2, text_color=WHITE)
        def leave(_=None):
            if not active:
                button.configure(fg_color="transparent", text_color=TEXT)
        button.bind("<Enter>", enter)
        button.bind("<Leave>", leave)
        return button

    # Navigation order: Dashboard → Schedule → other workspace pages.
    side_button("DASHBOARD", lambda: teacher_dashboard(app, teacher), True)
    side_button("SCHEDULE", lambda: teacher_my_schedule_page(app, teacher))
    side_button("ADD SCHEDULE", lambda: teacher_add_schedule_page(app, teacher))
    side_button("MY STUDENTS", lambda: teacher_my_students_page(app, teacher))
    side_button("ATTENDANCE CENTER", lambda: teacher_attendance_menu_page(app, teacher))
    side_button("STUDENTS", lambda: student_management_page(app, teacher))
    side_button("SUBJECTS", lambda: subject_management_page(app, teacher))
    side_button("CLASSES / SECTIONS", lambda: class_management_page(app, teacher))
    side_button("ATTENDANCE HISTORY", lambda: teacher_attendance_records_page(app, teacher))
    side_button("REPORTS", lambda: reports_page(app, teacher))
    side_button("BACKUP / RESTORE", lambda: backup_restore_page(app, teacher))

    ctk.CTkFrame(sidebar, fg_color="transparent").pack(fill="both", expand=True)

    # Animated online panel at the bottom of sidebar.
    online = ctk.CTkFrame(
        sidebar,
        fg_color=BG,
        corner_radius=12,
        border_width=1,
        border_color=BORDER
    )
    online.pack(fill="x", padx=14, pady=(8, 12))

    online_dot = ctk.CTkLabel(online, text="●", font=("Arial", 12), text_color=SUCCESS)
    online_dot.pack(side="left", padx=(12, 5), pady=11)
    ctk.CTkLabel(
        online,
        text="SYSTEM ONLINE",
        font=("Arial", 9, "bold"),
        text_color=SUCCESS
    ).pack(side="left")

    def pulse_dashboard_dot(step=0):
        try:
            if not online_dot.winfo_exists():
                return
            online_dot.configure(text_color=SUCCESS if step % 2 == 0 else "#A4F4C3")
            app.after(500, lambda: pulse_dashboard_dot(step + 1))
        except Exception:
            pass
    app.after(400, pulse_dashboard_dot)

    create_button(
        sidebar,
        "LOG OUT",
        lambda: role_selection(app),
        width=190,
        height=38,
        fg_color="#242B40",
        hover_color="#323B55"
    ).pack(padx=20, pady=(0, 22))

    # --------------------------------------------------------
    # MAIN AREA
    # --------------------------------------------------------
    main_area = ctk.CTkFrame(shell, fg_color=BG, corner_radius=0)
    main_area.pack(side="left", fill="both", expand=True)

    top = ctk.CTkFrame(main_area, fg_color="transparent", height=74)
    top.pack(fill="x", padx=30, pady=(18, 0))
    top.pack_propagate(False)

    title_box = ctk.CTkFrame(top, fg_color="transparent")
    title_box.pack(side="left", fill="y")

    ctk.CTkLabel(
        title_box,
        text="TEACHER / TC PORTAL",
        font=("Arial", 10, "bold"),
        text_color=PURPLE
    ).pack(anchor="w")

    ctk.CTkLabel(
        title_box,
        text="Dashboard",
        font=("Arial", 27, "bold"),
        text_color=WHITE
    ).pack(anchor="w")

    create_live_datetime(top).pack(side="right", pady=2)

    content = ctk.CTkScrollableFrame(main_area, fg_color="transparent")
    content.pack(fill="both", expand=True, padx=30, pady=(2, 20))

    # --------------------------------------------------------
    # HERO / WELCOME BANNER
    # --------------------------------------------------------
    hero = ctk.CTkFrame(
        content,
        fg_color=CARD,
        corner_radius=18,
        border_width=1,
        border_color=PURPLE
    )
    hero.pack(fill="x", pady=(8, 14))

    hero_left = ctk.CTkFrame(hero, fg_color="transparent")
    hero_left.pack(side="left", fill="both", expand=True, padx=24, pady=18)

    greeting_label = ctk.CTkLabel(
        hero_left,
        text="HI, " + teacher[2].upper() + "! 👋",
        font=("Arial", 13, "bold"),
        text_color=PURPLE
    )
    greeting_label.pack(anchor="w")

    ctk.CTkLabel(
        hero_left,
        text="READY TO MANAGE TODAY'S ATTENDANCE?",
        font=("Arial", 20, "bold"),
        text_color=WHITE
    ).pack(anchor="w", pady=(3, 3))

    ctk.CTkLabel(
        hero_left,
        text="Schedules, registered students and attendance records — all in one place.",
        font=("Arial", 10),
        text_color=TEXT
    ).pack(anchor="w")

    # Animated live indicator / accent on hero.
    hero_status = ctk.CTkLabel(
        hero,
        text="●  LIVE",
        font=("Arial", 10, "bold"),
        text_color=SUCCESS
    )
    hero_status.pack(side="right", padx=24, pady=18, anchor="n")

    def pulse_live(step=0):
        try:
            if not hero_status.winfo_exists():
                return
            hero_status.configure(text_color=SUCCESS if step % 2 == 0 else "#B8FFD0")
            app.after(550, lambda: pulse_live(step + 1))
        except Exception:
            pass
    app.after(300, pulse_live)

    # --------------------------------------------------------
    # ATTENDANCE PERIOD TABS
    # --------------------------------------------------------
    section_title = ctk.CTkFrame(content, fg_color="transparent")
    section_title.pack(fill="x", pady=(2, 5))
    ctk.CTkLabel(
        section_title,
        text="ATTENDANCE OVERVIEW",
        font=("Arial", 15, "bold"),
        text_color=WHITE
    ).pack(side="left")
    ctk.CTkLabel(
        section_title,
        text="Daily • Weekly • Monthly",
        font=("Arial", 9, "bold"),
        text_color=MUTED
    ).pack(side="right")

    period_bar = ctk.CTkFrame(content, fg_color="transparent")
    period_bar.pack(fill="x", pady=(0, 8))

    period_content = ctk.CTkFrame(content, fg_color="transparent")
    period_content.pack(fill="x")

    def show_period(period):
        for widget in period_content.winfo_children():
            widget.destroy()

        if period == "DAILY":
            summary = data["daily"]
            subtitle = "TODAY  •  " + data["today_date"]
        elif period == "WEEKLY":
            summary = data["weekly"]
            subtitle = "THIS WEEK  •  " + data["week_start"] + " → " + data["week_end"]
        else:
            summary = data["monthly"]
            subtitle = "THIS MONTH  •  " + data["month_start"] + " → " + data["month_end"]

        ctk.CTkLabel(
            period_content,
            text=subtitle,
            font=("Arial", 9, "bold"),
            text_color=MUTED
        ).pack(anchor="w", pady=(0, 5))

        cards = ctk.CTkFrame(period_content, fg_color="transparent")
        cards.pack(fill="x")

        stat_specs = [
            ("TOTAL RECORDS", summary[0], WHITE, "01"),
            ("PRESENT", summary[1], SUCCESS, "02"),
            ("LATE", summary[2], WARNING, "03"),
            ("ABSENT", summary[3], ERROR, "04")
        ]

        for index, (title, value, color, number) in enumerate(stat_specs):
            card = ctk.CTkFrame(
                cards,
                fg_color=CARD,
                corner_radius=15,
                border_width=1,
                border_color=BORDER
            )
            card.pack(side="left", fill="both", expand=True, padx=4)

            ctk.CTkLabel(
                card,
                text=number,
                font=("Arial", 8, "bold"),
                text_color=MUTED
            ).pack(anchor="ne", padx=12, pady=(9, 0))

            ctk.CTkLabel(
                card,
                text=title,
                font=("Arial", 9, "bold"),
                text_color=MUTED
            ).pack(anchor="w", padx=15, pady=(1, 0))

            number_label = ctk.CTkLabel(
                card,
                text="0",
                font=("Arial", 27, "bold"),
                text_color=color
            )
            number_label.pack(anchor="w", padx=15, pady=(0, 12))
            animate_number(app, number_label, value, delay=index * 80)

            # Tiny animated underline.
            underline = ctk.CTkFrame(card, height=3, width=1, fg_color=color, corner_radius=2)
            underline.place(x=15, y=card.winfo_reqheight() - 5)
            def grow_line(line=underline, target=105):
                try:
                    if not line.winfo_exists():
                        return
                    current = line.winfo_width()
                    if current < target:
                        line.configure(width=min(target, current + 12))
                        app.after(25, grow_line)
                except Exception:
                    pass
            app.after(80 + index * 70, grow_line)

        for button in period_bar.winfo_children():
            if isinstance(button, ctk.CTkButton):
                if button.cget("text") == period:
                    button.configure(fg_color=PURPLE, hover_color=PURPLE_HOVER, text_color=WHITE)
                else:
                    button.configure(fg_color=CARD, hover_color=CARD_2, text_color=TEXT)

    for period in ["DAILY", "WEEKLY", "MONTHLY"]:
        create_button(
            period_bar,
            period,
            lambda value=period: show_period(value),
            width=125,
            height=35,
            fg_color=CARD,
            hover_color=CARD_2
        ).pack(side="left", padx=(0, 7))

    show_period("DAILY")

    # --------------------------------------------------------
    # TODAY'S SCHEDULE
    # --------------------------------------------------------
    lower = ctk.CTkFrame(content, fg_color="transparent")
    lower.pack(fill="x", pady=(16, 10))

    schedule_col = ctk.CTkFrame(lower, fg_color="transparent")
    schedule_col.pack(fill="both", expand=True)

    sh = ctk.CTkFrame(schedule_col, fg_color="transparent")
    sh.pack(fill="x", pady=(0, 7))
    ctk.CTkLabel(sh, text="TODAY'S SCHEDULE", font=("Arial", 15, "bold"), text_color=WHITE).pack(side="left")
    ctk.CTkLabel(sh, text=data["today_day"], font=("Arial", 9, "bold"), text_color=PURPLE).pack(side="right")

    if not data["today_schedules"]:
        empty = ctk.CTkFrame(schedule_col, fg_color=CARD, corner_radius=14, border_width=1, border_color=BORDER)
        empty.pack(fill="x", pady=4)
        ctk.CTkLabel(empty, text="NO CLASS TODAY", font=("Arial", 15, "bold"), text_color=WHITE).pack(pady=(22, 3))
        ctk.CTkLabel(empty, text="No schedule is recorded for today.", font=("Arial", 10), text_color=MUTED).pack(pady=(0, 22))
    else:
        for index, item in enumerate(data["today_schedules"]):
            create_dashboard_schedule_card(schedule_col, item, show_day=False)

    create_button(
        schedule_col,
        "VIEW FULL SCHEDULE",
        lambda: teacher_my_schedule_page(app, teacher),
        width=190,
        height=36,
        fg_color=CARD,
        hover_color=CARD_2
    ).pack(anchor="w", pady=(8, 0))

    # --------------------------------------------------------
    # WEEKLY SCHEDULE REFERENCE
    # --------------------------------------------------------
    weekly_box = ctk.CTkFrame(content, fg_color="transparent")
    weekly_box.pack(fill="x", pady=(8, 18))

    wh = ctk.CTkFrame(weekly_box, fg_color="transparent")
    wh.pack(fill="x", pady=(0, 7))
    ctk.CTkLabel(wh, text="WEEKLY SCHEDULE", font=("Arial", 15, "bold"), text_color=WHITE).pack(side="left")
    ctk.CTkLabel(wh, text=str(len(data["weekly_schedules"])) + " class/es", font=("Arial", 9, "bold"), text_color=MUTED).pack(side="right")

    if not data["weekly_schedules"]:
        ctk.CTkLabel(weekly_box, text="No schedules available.", font=("Arial", 10), text_color=MUTED).pack(anchor="w")
    else:
        for index, item in enumerate(data["weekly_schedules"]):
            card = create_dashboard_schedule_card(weekly_box, item, show_day=True)
            # Visible staggered reveal.
            try:
                card.pack_forget()
                app.after(100 + index * 80, lambda c=card: c.pack(fill="x", pady=5))
            except Exception:
                pass

    # Keep the visible dashboard greeting in the hero; no extra duplicate toast here.


# ============================================================
# START APPLICATION
# ============================================================

def main():
    create_database()

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    app = ctk.CTk()

    app.title(APP_TITLE)
    app.geometry("1100x700")
    app.minsize(1000, 650)

    app.configure(fg_color=BG)

    role_selection(app)

    app.mainloop()



# ============================================================
# ATTENDX MAIN.PY UPGRADE LAYER
# ============================================================
# This section intentionally overrides only the UI/behavior that
# requires the current AttendX upgrade. The original application
# remains above this layer so existing working features stay
# available and backward compatible.

UPGRADE_VERSION = "2026.10.03-MAIN-UPGRADE"
QR_EXPIRATION_HOURS = 24
NAME_ALLOWED_CHARACTERS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 .'-")

def _column_exists(table_name, column_name):
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("PRAGMA table_info(" + table_name + ")")
        return any(row[1] == column_name for row in cursor.fetchall())
    finally:
        connection.close()


def _add_column_if_missing(table_name, column_name, definition):
    if _column_exists(table_name, column_name):
        return
    connection = get_connection()
    try:
        connection.execute(
            "ALTER TABLE " + table_name +
            " ADD COLUMN " + column_name + " " + definition
        )
        connection.commit()
    finally:
        connection.close()


def _ensure_attendx_upgrade_schema():
    connection = get_connection()
    cursor = connection.cursor()

    # --------------------------------------------------------
    # Backward-compatible student name structure.
    # Existing "name" is retained for every old module.
    # --------------------------------------------------------
    student_columns = [
        ("first_name", "TEXT DEFAULT ''"),
        ("last_name", "TEXT DEFAULT ''"),
        ("middle_name", "TEXT DEFAULT ''"),
        ("suffix", "TEXT DEFAULT ''"),
        ("sex", "TEXT DEFAULT ''"),
        ("status", "TEXT DEFAULT 'ACTIVE'"),
        ("created_at", "TEXT DEFAULT CURRENT_TIMESTAMP"),
        ("updated_at", "TEXT DEFAULT CURRENT_TIMESTAMP"),
    ]

    teacher_columns = [
        ("first_name", "TEXT DEFAULT ''"),
        ("last_name", "TEXT DEFAULT ''"),
        ("middle_name", "TEXT DEFAULT ''"),
        ("suffix", "TEXT DEFAULT ''"),
        ("role", "TEXT DEFAULT 'TEACHER'"),
        ("status", "TEXT DEFAULT 'ACTIVE'"),
        ("created_at", "TEXT DEFAULT CURRENT_TIMESTAMP"),
        ("updated_at", "TEXT DEFAULT CURRENT_TIMESTAMP"),
    ]

    # SQLite allows these ALTER operations because every added
    # column has a default value.
    for column_name, definition in student_columns:
        try:
            cursor.execute("PRAGMA table_info(students)")
            existing = {row[1] for row in cursor.fetchall()}
            if column_name not in existing:
                cursor.execute(
                    "ALTER TABLE students ADD COLUMN "
                    + column_name + " " + definition
                )
        except Exception:
            pass

    for column_name, definition in teacher_columns:
        try:
            cursor.execute("PRAGMA table_info(teachers)")
            existing = {row[1] for row in cursor.fetchall()}
            if column_name not in existing:
                cursor.execute(
                    "ALTER TABLE teachers ADD COLUMN "
                    + column_name + " " + definition
                )
        except Exception:
            pass

    # Centralized subjects.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_code TEXT UNIQUE NOT NULL,
            subject_name TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'ACTIVE',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Store the selected centralized subject code on schedules
    # without changing the existing subject column used by the
    # current AttendX modules.
    try:
        cursor.execute("PRAGMA table_info(schedules)")
        schedule_columns = {row[1] for row in cursor.fetchall()}
        if "subject_code" not in schedule_columns:
            cursor.execute(
                "ALTER TABLE schedules ADD COLUMN subject_code TEXT DEFAULT ''"
            )
    except Exception:
        pass

    # Preserve existing names while populating the new fields.
    try:
        cursor.execute("""
            SELECT id, name
            FROM students
            WHERE
                (first_name IS NULL OR TRIM(first_name) = '')
                AND name IS NOT NULL
                AND TRIM(name) <> ''
        """)
        rows = cursor.fetchall()
        for row in rows:
            parts = row[1].strip().split()
            first = parts[0] if parts else ""
            last = parts[-1] if len(parts) > 1 else first
            middle = " ".join(parts[1:-1]) if len(parts) > 2 else ""
            cursor.execute("""
                UPDATE students
                SET first_name = ?,
                    last_name = ?,
                    middle_name = COALESCE(middle_name, ''),
                    suffix = COALESCE(suffix, ''),
                    sex = COALESCE(sex, '')
                WHERE id = ?
            """, (first, last, middle, row[0]))
    except Exception:
        pass

    try:
        cursor.execute("""
            SELECT id, name
            FROM teachers
            WHERE
                (first_name IS NULL OR TRIM(first_name) = '')
                AND name IS NOT NULL
                AND TRIM(name) <> ''
        """)
        rows = cursor.fetchall()
        for row in rows:
            parts = row[1].strip().split()
            first = parts[0] if parts else ""
            last = parts[-1] if len(parts) > 1 else first
            middle = " ".join(parts[1:-1]) if len(parts) > 2 else ""
            cursor.execute("""
                UPDATE teachers
                SET first_name = ?,
                    last_name = ?,
                    middle_name = COALESCE(middle_name, ''),
                    suffix = COALESCE(suffix, '')
                WHERE id = ?
            """, (first, last, middle, row[0]))
    except Exception:
        pass

    # Create centralized subject records from existing schedules.
    try:
        cursor.execute("""
            SELECT DISTINCT TRIM(subject)
            FROM schedules
            WHERE subject IS NOT NULL
              AND TRIM(subject) <> ''
        """)
        existing_subjects = cursor.fetchall()
        for index, row in enumerate(existing_subjects, 1):
            subject_name = row[0].upper()
            cursor.execute("""
                SELECT id
                FROM subjects
                WHERE UPPER(subject_name) = UPPER(?)
            """, (subject_name,))
            found = cursor.fetchone()
            if found:
                subject_id = found[0]
            else:
                base_code = "".join(
                    ch for ch in subject_name.upper()
                    if ch.isalnum()
                )[:12]
                if not base_code:
                    base_code = "SUBJECT"
                subject_code = base_code
                counter = 1
                while True:
                    try:
                        cursor.execute(
                            "INSERT INTO subjects(subject_code, subject_name) VALUES (?, ?)",
                            (subject_code, subject_name)
                        )
                        subject_id = cursor.lastrowid
                        break
                    except sqlite3.IntegrityError:
                        counter += 1
                        subject_code = base_code[:9] + str(counter)
            cursor.execute("""
                UPDATE schedules
                SET subject_code = (
                    SELECT subject_code
                    FROM subjects
                    WHERE id = ?
                )
                WHERE UPPER(TRIM(subject)) = UPPER(TRIM(?))
                  AND (subject_code IS NULL OR TRIM(subject_code) = '')
            """, (subject_id, subject_name))
    except Exception:
        pass

    connection.commit()
    connection.close()


_original_create_database = _base_create_database

def create_database():
    _original_create_database()
    _ensure_attendx_upgrade_schema()


# ============================================================
# VALIDATION / NAME HELPERS
# ============================================================

def _normalize_text(value):
    return " ".join(str(value or "").strip().split())


def _valid_name(value, required=False):
    value = _normalize_text(value)
    if not value:
        return not required
    if len(value) > 80:
        return False
    if not any(ch.isalpha() for ch in value):
        return False
    for ch in value:
        if ch not in NAME_ALLOWED_CHARACTERS:
            return False
    return True


def _build_display_name(first_name, last_name, middle_name="", suffix=""):
    parts = [
        _normalize_text(first_name),
        _normalize_text(middle_name),
        _normalize_text(last_name),
        _normalize_text(suffix)
    ]
    return " ".join(part for part in parts if part)


def _valid_school_id(value):
    import re
    return re.fullmatch(r"\d{4}-\d{3}", value.strip()) is not None


def _get_course_values():
    connection = get_connection()
    cursor = connection.cursor()
    values = set()
    try:
        cursor.execute("SELECT course FROM students")
        values.update(
            str(row[0]).strip().upper()
            for row in cursor.fetchall()
            if row[0] and str(row[0]).strip()
        )
        cursor.execute("SELECT course FROM schedules")
        values.update(
            str(row[0]).strip().upper()
            for row in cursor.fetchall()
            if row[0] and str(row[0]).strip()
        )
    except Exception:
        pass
    finally:
        connection.close()

    # Keep the existing AttendX course usable on a fresh database
    # while still using a controlled selection.
    if not values:
        values.add("BSIT")

    return sorted(values)


def _get_section_values(course=None, year=None):
    connection = get_connection()
    cursor = connection.cursor()
    values = set()
    try:
        if course and year:
            cursor.execute("""
                SELECT section FROM students
                WHERE UPPER(TRIM(course)) = UPPER(TRIM(?))
                  AND UPPER(TRIM(year)) = UPPER(TRIM(?))
                UNION
                SELECT section FROM schedules
                WHERE UPPER(TRIM(course)) = UPPER(TRIM(?))
                  AND UPPER(TRIM(year)) = UPPER(TRIM(?))
            """, (course, year, course, year))
        else:
            cursor.execute("SELECT section FROM students UNION SELECT section FROM schedules")
        values.update(
            str(row[0]).strip().upper()
            for row in cursor.fetchall()
            if row[0] and str(row[0]).strip()
        )
    except Exception:
        pass
    finally:
        connection.close()

    # AttendX sections are controlled A-Z values. Existing
    # database values are preserved and added to the choices.
    for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        values.add(letter)

    return sorted(values)


def _make_combo(parent, values, default=None, width=None):
    kwargs = {
        "values": values,
        "height": 44,
        "corner_radius": 8,
        "fg_color": CARD_2,
        "border_color": BORDER,
        "button_color": PURPLE,
        "button_hover_color": PURPLE_HOVER,
        "text_color": WHITE
    }
    if width:
        kwargs["width"] = width
    combo = ctk.CTkComboBox(parent, **kwargs)
    if values:
        combo.set(default if default in values else values[0])
    return combo


# ============================================================
# STUDENT REGISTRATION — FOUR-PART NAME STRUCTURE
# ============================================================

def student_register_page(app):
    clear_screen(app)
    create_top_bar(app, app, True, lambda: student_portal(app))
    create_page_title(
        app,
        "CREATE STUDENT ACCOUNT",
        "Use the student's official information."
    )

    form = ctk.CTkScrollableFrame(
        app,
        width=650,
        height=610,
        fg_color=CARD,
        corner_radius=18,
        border_width=1,
        border_color=BORDER
    )
    form.pack(fill="both", expand=True, padx=80, pady=(5, 20))

    ctk.CTkLabel(
        form, text="Student Registration",
        font=("Arial", 22, "bold"), text_color=WHITE
    ).pack(pady=(20, 12))

    school_id = create_input(form, "Student ID / School ID  (YYYY-###)")
    first_name = create_input(form, "First Name *")
    last_name = create_input(form, "Last Name *")
    middle_name = create_input(form, "Middle Name (Optional)")
    suffix = create_input(form, "Extension / Suffix (Optional)")

    ctk.CTkLabel(
        form, text="Sex", font=("Arial", 10, "bold"),
        text_color=MUTED
    ).pack(anchor="w", padx=2, pady=(7, 0))
    sex = _make_combo(form, ["Male", "Female"], "Male")
    sex.pack(fill="x", pady=6)

    ctk.CTkLabel(
        form, text="Course", font=("Arial", 10, "bold"),
        text_color=MUTED
    ).pack(anchor="w", padx=2, pady=(7, 0))
    course = _make_combo(form, _get_course_values())
    course.pack(fill="x", pady=6)

    ctk.CTkLabel(
        form, text="Year", font=("Arial", 10, "bold"),
        text_color=MUTED
    ).pack(anchor="w", padx=2, pady=(7, 0))
    year = _make_combo(form, ["1ST", "2ND", "3RD", "4TH"], "1ST")
    year.pack(fill="x", pady=6)

    ctk.CTkLabel(
        form, text="Section", font=("Arial", 10, "bold"),
        text_color=MUTED
    ).pack(anchor="w", padx=2, pady=(7, 0))
    section = _make_combo(
        form,
        _get_section_values(course.get(), year.get()),
        "A"
    )
    section.pack(fill="x", pady=6)

    def refresh_sections(_value=None):
        values = _get_section_values(course.get(), year.get())
        section.configure(values=values)
        if section.get() not in values:
            section.set(values[0])

    course.configure(command=refresh_sections)
    year.configure(command=refresh_sections)

    password = create_input(form, "Password", show="*")
    confirm = create_input(form, "Confirm Password", show="*")

    def register():
        sid = _normalize_text(school_id.get())
        first = _normalize_text(first_name.get())
        last = _normalize_text(last_name.get())
        middle = _normalize_text(middle_name.get())
        extension = _normalize_text(suffix.get())
        sex_value = _normalize_text(sex.get()).title()
        course_value = _normalize_text(course.get()).upper()
        year_value = _normalize_text(year.get()).upper()
        section_value = _normalize_text(section.get()).upper()
        pass_value = password.get()
        confirm_value = confirm.get()

        if not sid or not first or not last or not course_value or not year_value or not section_value:
            messagebox.showerror("Registration Error", "Please complete all required fields.")
            return

        if not _valid_school_id(sid):
            messagebox.showerror(
                "Registration Error",
                "Student ID must use the format YYYY-###."
            )
            return

        if not _valid_name(first, True) or not _valid_name(last, True):
            messagebox.showerror(
                "Registration Error",
                "First Name and Last Name must contain valid name values."
            )
            return

        if not _valid_name(middle) or not _valid_name(extension):
            messagebox.showerror(
                "Registration Error",
                "Middle Name or Extension/Suffix contains invalid characters."
            )
            return

        if sex_value not in ("Male", "Female"):
            messagebox.showerror(
                "Registration Error",
                "Sex must be Male or Female."
            )
            return

        if len(pass_value) < 6:
            messagebox.showerror(
                "Registration Error",
                "Password must contain at least 6 characters."
            )
            return

        if pass_value != confirm_value:
            messagebox.showerror(
                "Registration Error",
                "Passwords do not match."
            )
            return

        display_name = _build_display_name(first, last, middle, extension)

        connection = get_connection()
        try:
            connection.execute("""
                INSERT INTO students
                (
                    school_id, password, name,
                    course, year, section,
                    first_name, last_name, middle_name, suffix, sex, status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE')
            """, (
                sid,
                hash_password(pass_value),
                display_name,
                course_value,
                year_value,
                section_value,
                first,
                last,
                middle,
                extension,
                sex_value
            ))
            connection.commit()
            messagebox.showinfo(
                "Account Created",
                "Student account successfully created.\n\nHi "
                + display_name + "! Your AttendX account is ready."
            )
            student_login_page(app)
        except sqlite3.IntegrityError:
            messagebox.showerror(
                "Registration Error",
                "School ID already exists. Please use another School ID."
            )
        except Exception as error:
            connection.rollback()
            messagebox.showerror(
                "Registration Error",
                "Unable to create the student account.\n\n" + str(error)
            )
        finally:
            connection.close()

    create_button(form, "CREATE ACCOUNT", register, width=300).pack(pady=(15, 8))
    create_button(
        form, "BACK", lambda: student_portal(app), width=300,
        fg_color="#242B40", hover_color="#323B55"
    ).pack(pady=(0, 20))


# ============================================================
# TEACHER / TC REGISTRATION
# ============================================================

def teacher_register_page(app, account_role="TEACHER"):
    clear_screen(app)
    create_top_bar(app, app, True, lambda: teacher_portal(app))
    role_value = "TC" if str(account_role).upper() == "TC" else "TEACHER"

    form = ctk.CTkScrollableFrame(
        app,
        width=650,
        height=610,
        fg_color=CARD,
        corner_radius=18,
        border_width=1,
        border_color=BORDER
    )
    form.pack(fill="both", expand=True, padx=80, pady=(5, 20))

    create_page_title(
        app,
        "CREATE " + role_value + " ACCOUNT",
        "Enter the official " + role_value + " information."
    )

    ctk.CTkLabel(
        form, text=role_value + " Registration",
        font=("Arial", 22, "bold"), text_color=WHITE
    ).pack(pady=(20, 12))

    teacher_id = create_input(
        form,
        ("TC ID" if role_value == "TC" else "Teacher ID")
    )
    first_name = create_input(form, "First Name *")
    last_name = create_input(form, "Last Name *")
    middle_name = create_input(form, "Middle Name (Optional)")
    suffix = create_input(form, "Extension / Suffix (Optional)")
    password = create_input(form, "Password", show="*")
    confirm = create_input(form, "Confirm Password", show="*")

    def register():
        tid = _normalize_text(teacher_id.get())
        first = _normalize_text(first_name.get())
        last = _normalize_text(last_name.get())
        middle = _normalize_text(middle_name.get())
        extension = _normalize_text(suffix.get())
        pass_value = password.get()
        confirm_value = confirm.get()

        if not tid or not first or not last:
            messagebox.showerror(
                "Registration Error",
                "Teacher/TC ID, First Name and Last Name are required."
            )
            return

        if not _valid_name(first, True) or not _valid_name(last, True):
            messagebox.showerror(
                "Registration Error",
                "First Name and Last Name must contain valid name values."
            )
            return

        if not _valid_name(middle) or not _valid_name(extension):
            messagebox.showerror(
                "Registration Error",
                "Middle Name or Extension/Suffix contains invalid characters."
            )
            return

        if len(pass_value) < 6:
            messagebox.showerror(
                "Registration Error",
                "Password must contain at least 6 characters."
            )
            return

        if pass_value != confirm_value:
            messagebox.showerror(
                "Registration Error",
                "Passwords do not match."
            )
            return

        display_name = _build_display_name(first, last, middle, extension)

        connection = get_connection()
        try:
            connection.execute("""
                INSERT INTO teachers
                (
                    teacher_id, password, name,
                    first_name, last_name, middle_name, suffix,
                    role, status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE')
            """, (
                tid,
                hash_password(pass_value),
                display_name,
                first,
                last,
                middle,
                extension,
                role_value
            ))
            connection.commit()
            messagebox.showinfo(
                "Account Created",
                role_value + " account successfully created.\n\nHi "
                + display_name + "! Your AttendX account is ready."
            )
            teacher_login_page(app, role_value)
        except sqlite3.IntegrityError:
            messagebox.showerror(
                "Registration Error",
                "ID already exists. Please use another ID."
            )
        except Exception as error:
            connection.rollback()
            messagebox.showerror(
                "Registration Error",
                "Unable to create the account.\n\n" + str(error)
            )
        finally:
            connection.close()

    create_button(form, "CREATE ACCOUNT", register, width=300).pack(pady=(15, 8))
    create_button(
        form, "BACK", lambda: teacher_portal(app), width=300,
        fg_color="#242B40", hover_color="#323B55"
    ).pack(pady=(0, 20))


# ============================================================
# TEACHER / TC LOGIN
# ============================================================

def teacher_login_page(app, forced_role=None):
    clear_screen(app)
    role_filter = str(forced_role or "").upper().strip()

    create_top_bar(
        app, app, True,
        lambda: role_selection(app)
    )

    title = "TC LOGIN" if role_filter == "TC" else "TEACHER LOGIN"
    create_page_title(
        app,
        title,
        "Login using your " + ("TC ID" if role_filter == "TC" else "Teacher ID") + " and password."
    )

    form = ctk.CTkFrame(
        app, width=500, height=430, fg_color=CARD,
        corner_radius=18, border_width=1, border_color=BORDER
    )
    form.pack(expand=True)
    form.pack_propagate(False)

    ctk.CTkLabel(
        form, text="Welcome Back",
        font=("Arial", 24, "bold"), text_color=WHITE
    ).pack(pady=(30, 15))

    account_id = create_input(
        form,
        "TC ID" if role_filter == "TC" else "Teacher ID"
    )
    password = create_input(form, "Password", show="*")

    def login():
        tid = _normalize_text(account_id.get())
        pass_value = password.get()

        if not tid or not pass_value:
            messagebox.showerror(
                "Login Error",
                "Please enter your ID and password."
            )
            return

        connection = get_connection()
        cursor = connection.cursor()
        try:
            if _column_exists("teachers", "role"):
                cursor.execute("""
                    SELECT id, teacher_id, name, role, status
                    FROM teachers
                    WHERE teacher_id = ? AND password = ?
                """, (tid, hash_password(pass_value)))
                row = cursor.fetchone()
            else:
                cursor.execute("""
                    SELECT id, teacher_id, name, 'TEACHER', 'ACTIVE'
                    FROM teachers
                    WHERE teacher_id = ? AND password = ?
                """, (tid, hash_password(pass_value)))
                row = cursor.fetchone()
        finally:
            connection.close()

        if not row:
            messagebox.showerror("Login Failed", "Invalid ID or password.")
            return

        actual_role = str(row[3] or "TEACHER").upper()
        status = str(row[4] or "ACTIVE").upper()

        if status != "ACTIVE":
            messagebox.showerror(
                "Login Blocked",
                "This account is currently inactive."
            )
            return

        if role_filter and actual_role != role_filter:
            messagebox.showerror(
                "Role Mismatch",
                "This account is registered as " + actual_role + "."
            )
            return

        global CURRENT_USER_NAME, CURRENT_USER_ROLE
        CURRENT_USER_NAME = row[2]
        CURRENT_USER_ROLE = actual_role.lower()

        teacher_record = (row[0], row[1], row[2])

        if actual_role == "TC":
            tc_dashboard(app, teacher_record)
        else:
            teacher_dashboard(app, teacher_record)

    create_button(form, "LOG IN", login, width=300).pack(pady=(15, 8))
    create_button(
        form, "CREATE ACCOUNT",
        lambda: teacher_register_page(
            app,
            "TC" if role_filter == "TC" else "TEACHER"
        ),
        width=300
    ).pack(pady=8)
    create_button(
        form, "FORGOT PASSWORD",
        lambda: teacher_forgot_password(app),
        width=300,
        fg_color="#242B40",
        hover_color="#323B55"
    ).pack(pady=8)


# ============================================================
# ROLE SELECTION — STUDENT / TEACHER / TC
# ============================================================

def role_selection(app):
    global CURRENT_USER_NAME, CURRENT_USER_ROLE
    CURRENT_USER_NAME = ""
    CURRENT_USER_ROLE = ""
    clear_screen(app)
    create_top_bar(app, app)

    ctk.CTkLabel(
        app,
        text="WELCOME TO ATTENDX",
        font=("Arial", 34, "bold"),
        text_color=WHITE
    ).pack(pady=(30, 4))

    ctk.CTkLabel(
        app,
        text="Smart School Attendance Management System",
        font=("Arial", 14),
        text_color=MUTED
    ).pack(pady=(0, 25))

    cards = ctk.CTkFrame(app, fg_color="transparent")
    cards.pack(expand=True)

    roles = [
        (
            "STUDENT",
            "Manage subjects, profile and attendance.",
            lambda: student_portal(app)
        ),
        (
            "TEACHER",
            "Manage schedules, students and attendance.",
            lambda: teacher_portal(app)
        ),
        (
            "TC",
            "Teacher Coordinator access for classes, verification and management.",
            lambda: teacher_login_page(app, "TC")
        )
    ]

    for title, description, command in roles:
        card = ctk.CTkFrame(
            cards, width=300, height=300, fg_color=CARD,
            corner_radius=18, border_width=1, border_color=BORDER
        )
        card.pack(side="left", padx=10)
        card.pack_propagate(False)

        ctk.CTkLabel(
            card, text=title,
            font=("Arial", 24, "bold"), text_color=WHITE
        ).pack(pady=(38, 12))

        ctk.CTkLabel(
            card, text=description,
            font=("Arial", 11), text_color=TEXT,
            justify="center", wraplength=245
        ).pack(pady=5)

        create_button(
            card,
            "ENTER " + title + " PORTAL",
            command,
            width=230
        ).pack(pady=25)

    bottom = ctk.CTkFrame(app, fg_color="transparent")
    bottom.pack(pady=(0, 20))
    create_button(
        bottom, "USER GUIDE", lambda: show_user_guide(app),
        width=160, height=38, fg_color=CARD, hover_color=CARD_2
    ).pack(side="left", padx=5)
    create_button(
        bottom, "EXIT SYSTEM", app.destroy,
        width=160, height=38, fg_color="#242B40", hover_color="#323B55"
    ).pack(side="left", padx=5)


# ============================================================
# STUDENT DASHBOARD — ABSENCE / DROP STATUS
# ============================================================

def _get_student_absence_count(student_id):
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("""
            SELECT COUNT(*)
            FROM attendance
            WHERE student_id = ?
              AND UPPER(status) = 'ABSENT'
        """, (student_id,))
        return int(cursor.fetchone()[0] or 0)
    except Exception:
        return 0
    finally:
        connection.close()


def student_dashboard(app, student):
    clear_screen(app)
    create_top_bar(app, app)

    absence_count = _get_student_absence_count(student[0])
    drop_flag = absence_count >= 3

    welcome = ctk.CTkFrame(app, fg_color="transparent")
    welcome.pack(fill="x", padx=50, pady=(18, 0))

    ctk.CTkLabel(
        welcome,
        text="HI, " + str(student[2]).upper() + "! 👋",
        font=("Arial", 20, "bold"), text_color=WHITE
    ).pack(anchor="w")

    ctk.CTkLabel(
        welcome,
        text="You're back. Here's your AttendX student account.",
        font=("Arial", 11), text_color=MUTED
    ).pack(anchor="w", pady=(2, 0))

    profile = ctk.CTkFrame(
        app, fg_color=CARD, height=180, corner_radius=15,
        border_width=1, border_color=ERROR if drop_flag else BORDER
    )
    profile.pack(fill="x", padx=50, pady=(20, 15))
    profile.pack_propagate(False)

    left = ctk.CTkFrame(profile, fg_color="transparent")
    left.pack(side="left", padx=30, pady=20)

    ctk.CTkLabel(
        left, text=student[2],
        font=("Arial", 25, "bold"), text_color=WHITE
    ).pack(anchor="w")

    ctk.CTkLabel(
        left, text="Student ID: " + student[1],
        font=("Arial", 11), text_color=MUTED
    ).pack(anchor="w", pady=4)

    ctk.CTkLabel(
        left,
        text=str(student[3]) + "  •  " + str(student[4]) + " Year  •  Section " + str(student[5]),
        font=("Arial", 12), text_color=TEXT
    ).pack(anchor="w")

    status_text = "FLAG FOR DROP" if drop_flag else "ACTIVE"
    status_color = ERROR if drop_flag else SUCCESS

    ctk.CTkLabel(
        left,
        text="ABSENCES: " + str(absence_count) + " / 3",
        font=("Arial", 12, "bold"), text_color=status_color
    ).pack(anchor="w", pady=(5, 0))

    ctk.CTkLabel(
        left,
        text=status_text,
        font=("Arial", 12, "bold"), text_color=status_color
    ).pack(anchor="w", pady=(2, 0))

    profile_right = ctk.CTkFrame(profile, fg_color="transparent")
    profile_right.pack(side="right", padx=25, pady=15)
    create_live_datetime(profile_right).pack(anchor="e")
    ctk.CTkLabel(
        profile_right, text="STUDENT",
        font=("Arial", 11, "bold"), text_color=PURPLE
    ).pack(anchor="e", pady=(5, 0))

    menu = ctk.CTkFrame(app, fg_color="transparent")
    menu.pack(expand=True)

    buttons = [
        ("ADD MY SUBJECT", "Connect yourself to a class using your teacher information.",
         lambda: student_add_subject_page(app, student)),
        ("MY SUBJECTS", "View your currently enrolled classes.",
         lambda: student_my_subjects_page(app, student)),
        ("MY ATTENDANCE", "View your attendance history and status.",
         lambda: student_attendance_page(app, student)),
        ("MY PROFILE", "View your information and class QR codes.",
         lambda: student_profile_page(app, student))
    ]

    for title, description, command in buttons:
        card = ctk.CTkFrame(
            menu, width=800, height=75, fg_color=CARD,
            corner_radius=12, border_width=1, border_color=BORDER
        )
        card.pack(pady=6)
        card.pack_propagate(False)
        create_button(card, title, command, width=190).pack(
            side="left", padx=15, pady=16
        )
        ctk.CTkLabel(
            card, text=description,
            font=("Arial", 11), text_color=TEXT
        ).pack(side="left", padx=10)

    create_button(
        app, "LOG OUT", lambda: role_selection(app),
        width=180, fg_color="#242B40", hover_color="#323B55"
    ).pack(pady=(5, 25))


# ============================================================
# CENTRAL SUBJECT MANAGEMENT
# ============================================================

def subject_management_page(app, teacher):
    clear_screen(app)
    create_top_bar(
        app, app, True,
        lambda: tc_dashboard(app, teacher) if CURRENT_USER_ROLE == "tc"
        else teacher_dashboard(app, teacher)
    )
    create_page_title(
        app, "SUBJECTS",
        "Centralized Subject Code and Subject Name management."
    )

    shell = ctk.CTkFrame(app, fg_color="transparent")
    shell.pack(fill="both", expand=True, padx=55, pady=5)

    form = ctk.CTkFrame(
        shell, fg_color=CARD, corner_radius=15,
        border_width=1, border_color=BORDER
    )
    form.pack(fill="x", pady=(0, 10))

    code_entry = create_input(form, "Subject Code")
    name_entry = create_input(form, "Subject Name")

    list_frame = ctk.CTkScrollableFrame(
        shell, fg_color="transparent"
    )
    list_frame.pack(fill="both", expand=True)

    def load_subjects():
        for widget in list_frame.winfo_children():
            widget.destroy()

        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute("""
            SELECT id, subject_code, subject_name, status
            FROM subjects
            ORDER BY subject_code
        """)
        rows = cursor.fetchall()
        connection.close()

        if not rows:
            ctk.CTkLabel(
                list_frame, text="No subjects registered.",
                font=("Arial", 14), text_color=MUTED
            ).pack(pady=40)
            return

        for row in rows:
            card = ctk.CTkFrame(
                list_frame, fg_color=CARD, corner_radius=12,
                border_width=1, border_color=BORDER
            )
            card.pack(fill="x", pady=5)
            ctk.CTkLabel(
                card, text=row[1] + "  |  " + row[2],
                font=("Arial", 13, "bold"), text_color=WHITE
            ).pack(side="left", padx=16, pady=12)
            ctk.CTkLabel(
                card, text=row[3],
                font=("Arial", 10, "bold"),
                text_color=SUCCESS if row[3] == "ACTIVE" else WARNING
            ).pack(side="right", padx=16)

    def add_subject():
        code = _normalize_text(code_entry.get()).upper()
        name = _normalize_text(name_entry.get()).upper()

        if not code or not name:
            messagebox.showerror("Subject Error", "Subject Code and Subject Name are required.")
            return
        if len(code) > 30 or len(name) > 120:
            messagebox.showerror("Subject Error", "Subject Code or Name is too long.")
            return

        connection = get_connection()
        try:
            connection.execute("""
                INSERT INTO subjects(subject_code, subject_name)
                VALUES (?, ?)
            """, (code, name))
            connection.commit()
            code_entry.delete(0, "end")
            name_entry.delete(0, "end")
            load_subjects()
        except sqlite3.IntegrityError:
            messagebox.showerror(
                "Subject Error",
                "Subject Code already exists."
            )
        finally:
            connection.close()

    create_button(
        form, "ADD SUBJECT", add_subject, width=200
    ).pack(pady=(0, 15))
    load_subjects()


# ============================================================
# CLASS / SECTION MANAGEMENT
# ============================================================

def class_management_page(app, teacher):
    clear_screen(app)
    create_top_bar(
        app, app, True,
        lambda: tc_dashboard(app, teacher) if CURRENT_USER_ROLE == "tc"
        else teacher_dashboard(app, teacher)
    )
    create_page_title(
        app, "CLASSES / SECTIONS",
        "Review Course, Year, Section, Subject and Teacher/TC assignments."
    )

    search = create_input(app, "Search ID, Course, Year, Section or Subject")
    search.pack(fill="x", padx=55, pady=(0, 8))

    container = ctk.CTkScrollableFrame(app, fg_color="transparent")
    container.pack(fill="both", expand=True, padx=55, pady=5)

    def load():
        for widget in container.winfo_children():
            widget.destroy()

        query = _normalize_text(search.get()).upper()

        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute("""
            SELECT
                schedules.id,
                schedules.course,
                schedules.year,
                schedules.section,
                schedules.subject,
                schedules.day,
                schedules.start_time,
                schedules.end_time,
                teachers.name,
                teachers.teacher_id,
                COALESCE(teachers.role, 'TEACHER')
            FROM schedules
            INNER JOIN teachers ON schedules.teacher_id = teachers.id
            ORDER BY schedules.course, schedules.year, schedules.section,
                     schedules.subject, schedules.day, schedules.start_time
        """)
        rows = cursor.fetchall()
        connection.close()

        rows = [
            row for row in rows
            if not query or query in " ".join(str(x).upper() for x in row)
        ]

        if not rows:
            ctk.CTkLabel(
                container, text="No matching classes found.",
                font=("Arial", 14), text_color=MUTED
            ).pack(pady=50)
            return

        for row in rows:
            card = ctk.CTkFrame(
                container, fg_color=CARD, corner_radius=12,
                border_width=1, border_color=BORDER
            )
            card.pack(fill="x", pady=5)

            ctk.CTkLabel(
                card,
                text=row[4] + "  |  " + row[1] + " | " + row[2] + " | Section " + row[3],
                font=("Arial", 13, "bold"), text_color=WHITE
            ).pack(anchor="w", padx=16, pady=(12, 4))

            ctk.CTkLabel(
                card,
                text=(
                    row[5] + "  " + format_time_12h(row[6])
                    + " - " + format_time_12h(row[7])
                    + "  |  " + row[10] + ": " + row[8]
                    + "  |  ID: " + row[9]
                ),
                font=("Arial", 10), text_color=TEXT
            ).pack(anchor="w", padx=16, pady=(0, 12))

    create_button(
        app, "SEARCH / REFRESH", load, width=180, height=38
    ).pack(pady=(0, 8))
    load()


# ============================================================
# STUDENT MANAGEMENT
# ============================================================

def student_management_page(app, teacher):
    clear_screen(app)
    create_top_bar(
        app, app, True,
        lambda: tc_dashboard(app, teacher) if CURRENT_USER_ROLE == "tc"
        else teacher_dashboard(app, teacher)
    )
    create_page_title(
        app, "STUDENTS",
        "Search, view and activate/deactivate student accounts."
    )

    search = create_input(app, "Search ID, Name, Course, Year or Section")
    search.pack(fill="x", padx=55, pady=(0, 8))
    container = ctk.CTkScrollableFrame(app, fg_color="transparent")
    container.pack(fill="both", expand=True, padx=55, pady=5)

    def load():
        for widget in container.winfo_children():
            widget.destroy()

        query = _normalize_text(search.get()).upper()
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute("""
            SELECT id, school_id, name, sex, course, year, section,
                   COALESCE(status, 'ACTIVE')
            FROM students
            ORDER BY name
        """)
        rows = cursor.fetchall()
        connection.close()

        rows = [
            row for row in rows
            if not query or query in " ".join(str(x).upper() for x in row)
        ]

        for row in rows:
            card = ctk.CTkFrame(
                container, fg_color=CARD, corner_radius=12,
                border_width=1, border_color=BORDER
            )
            card.pack(fill="x", pady=5)

            ctk.CTkLabel(
                card,
                text=row[2] + "  |  " + row[1],
                font=("Arial", 13, "bold"), text_color=WHITE
            ).pack(side="left", padx=16, pady=12)

            ctk.CTkLabel(
                card,
                text=(
                    str(row[3] or "")
                    + " | " + row[4]
                    + " | " + row[5]
                    + " | Section " + row[6]
                ),
                font=("Arial", 10), text_color=TEXT
            ).pack(side="left", padx=10)

            def toggle(student_id=row[0], current=row[7]):
                new_status = "INACTIVE" if current == "ACTIVE" else "ACTIVE"
                connection = get_connection()
                connection.execute(
                    "UPDATE students SET status = ? WHERE id = ?",
                    (new_status, student_id)
                )
                connection.commit()
                connection.close()
                load()

            create_button(
                card,
                row[7],
                toggle,
                width=105,
                height=34,
                fg_color=SUCCESS if row[7] == "ACTIVE" else WARNING,
                hover_color=SUCCESS if row[7] == "ACTIVE" else WARNING
            ).pack(side="right", padx=12)

    create_button(
        app, "SEARCH / REFRESH", load, width=180, height=38
    ).pack(pady=(0, 8))
    load()


# ============================================================
# TC MANAGEMENT
# ============================================================

def tc_management_page(app, teacher):
    clear_screen(app)
    create_top_bar(app, app, True, lambda: tc_dashboard(app, teacher))
    create_page_title(
        app, "TC MANAGEMENT",
        "Manage Teacher Coordinator accounts."
    )

    search = create_input(app, "Search TC ID or Name")
    search.pack(fill="x", padx=55, pady=(0, 8))
    container = ctk.CTkScrollableFrame(app, fg_color="transparent")
    container.pack(fill="both", expand=True, padx=55, pady=5)

    def load():
        for widget in container.winfo_children():
            widget.destroy()

        query = _normalize_text(search.get()).upper()
        connection = get_connection()
        cursor = connection.cursor()
        cursor.execute("""
            SELECT id, teacher_id, name, status
            FROM teachers
            WHERE UPPER(COALESCE(role, 'TEACHER')) = 'TC'
            ORDER BY name
        """)
        rows = cursor.fetchall()
        connection.close()

        rows = [
            row for row in rows
            if not query or query in (str(row[1]) + " " + str(row[2])).upper()
        ]

        if not rows:
            ctk.CTkLabel(
                container, text="No TC accounts found.",
                font=("Arial", 14), text_color=MUTED
            ).pack(pady=40)
            return

        for row in rows:
            card = ctk.CTkFrame(
                container, fg_color=CARD, corner_radius=12,
                border_width=1, border_color=BORDER
            )
            card.pack(fill="x", pady=5)

            ctk.CTkLabel(
                card, text=row[2] + "  |  " + row[1],
                font=("Arial", 13, "bold"), text_color=WHITE
            ).pack(side="left", padx=16, pady=12)

            def toggle(tc_id=row[0], current=row[3]):
                new_status = "INACTIVE" if str(current).upper() == "ACTIVE" else "ACTIVE"
                connection = get_connection()
                connection.execute(
                    "UPDATE teachers SET status = ? WHERE id = ?",
                    (new_status, tc_id)
                )
                connection.commit()
                connection.close()
                load()

            create_button(
                card, row[3], toggle, width=105, height=34,
                fg_color=SUCCESS if str(row[3]).upper() == "ACTIVE" else WARNING,
                hover_color=SUCCESS if str(row[3]).upper() == "ACTIVE" else WARNING
            ).pack(side="right", padx=12)

    create_button(
        app, "SEARCH / REFRESH", load, width=180, height=38
    ).pack(pady=(0, 8))
    load()


# ============================================================
# TEACHER/TC FACE REGISTRATION
# ============================================================

def teacher_face_register_action(teacher):
    try:
        success = register_teacher_face(teacher[0])
        if success:
            messagebox.showinfo(
                "FACE REGISTRATION",
                "Teacher/TC face registration completed successfully."
            )
        else:
            messagebox.showwarning(
                "FACE REGISTRATION",
                "Face registration was cancelled or could not be completed."
            )
    except Exception as error:
        messagebox.showerror(
            "FACE REGISTRATION ERROR",
            "Unable to register the Teacher/TC face.\n\n" + str(error)
        )


# ============================================================
# TC DASHBOARD
# ============================================================

def tc_dashboard(app, teacher):
    clear_screen(app)
    create_top_bar(app, app)

    ctk.CTkLabel(
        app, text="TC CONTROL CENTER",
        font=("Arial", 29, "bold"), text_color=WHITE
    ).pack(anchor="w", padx=50, pady=(25, 3))

    ctk.CTkLabel(
        app,
        text="Welcome, " + str(teacher[2]) + ". TC access is active.",
        font=("Arial", 12), text_color=MUTED
    ).pack(anchor="w", padx=50)

    grid = ctk.CTkFrame(app, fg_color="transparent")
    grid.pack(fill="both", expand=True, padx=45, pady=20)

    actions = [
        ("DASHBOARD", lambda: tc_dashboard(app, teacher)),
        ("STUDENTS", lambda: student_management_page(app, teacher)),
        ("SUBJECTS", lambda: subject_management_page(app, teacher)),
        ("CLASSES / SECTIONS", lambda: class_management_page(app, teacher)),
        ("ADD SCHEDULE", lambda: teacher_add_schedule_page(app, teacher)),
        ("SCHEDULES", lambda: teacher_my_schedule_page(app, teacher)),
        ("ATTENDANCE", lambda: teacher_attendance_page(app, teacher)),
        ("ATTENDANCE HISTORY", lambda: teacher_attendance_records_page(app, teacher)),
        ("REPORTS", lambda: reports_page(app, teacher)),
        ("BACKUP / RESTORE", lambda: backup_restore_page(app, teacher)),
        ("TC MANAGEMENT", lambda: tc_management_page(app, teacher)),
        ("REGISTER TC FACE", lambda: teacher_face_register_action(teacher)),
        ("CHECK FINGERPRINT", lambda: fingerprint_status_page(app, teacher)),
        ("LOG OUT", lambda: role_selection(app))
    ]

    for index, (title, command) in enumerate(actions):
        card = ctk.CTkFrame(
            grid, fg_color=CARD, corner_radius=13,
            border_width=1, border_color=BORDER
        )
        row = index // 3
        col = index % 3
        card.grid(row=row, column=col, padx=7, pady=7, sticky="nsew")
        ctk.CTkLabel(
            card, text=title,
            font=("Arial", 12, "bold"), text_color=WHITE
        ).pack(pady=(20, 8))
        create_button(
            card, "OPEN", command, width=145, height=36
        ).pack(pady=(0, 18))

    for col in range(3):
        grid.grid_columnconfigure(col, weight=1)
    for row in range((len(actions) + 2) // 3):
        grid.grid_rowconfigure(row, weight=1)


# ============================================================
# ATTENDANCE STATUS — 15-MINUTE RULE
# ============================================================

def get_attendance_status(start_time, current_time=None):
    if current_time is None:
        current_time = datetime.now().strftime("%H:%M:%S")

    try:
        start_parts = str(start_time).split(":")
        current_parts = str(current_time).split(":")
        start_minutes = int(start_parts[0]) * 60 + int(start_parts[1])
        current_minutes = int(current_parts[0]) * 60 + int(current_parts[1])
    except Exception:
        return "ABSENT"

    elapsed = current_minutes - start_minutes

    if elapsed < 0:
        return "LATE"

    if elapsed < 15:
        return "LATE"

    return "ABSENT"


# ============================================================
# ATTENDANCE RECORDING — CENTRAL VALIDATION
# ============================================================

def record_attendance(student_id, schedule_id, method):
    now = datetime.now()
    attendance_date = now.strftime("%Y-%m-%d")
    attendance_time = now.strftime("%H:%M:%S")

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT
                students.id,
                students.school_id,
                students.name,
                students.course,
                students.year,
                students.section,
                COALESCE(students.status, 'ACTIVE'),
                schedules.id,
                schedules.teacher_id,
                schedules.subject,
                schedules.course,
                schedules.year,
                schedules.section,
                schedules.start_time
            FROM students
            INNER JOIN student_classes
                ON student_classes.student_id = students.id
            INNER JOIN schedules
                ON schedules.id = student_classes.schedule_id
            WHERE students.id = ?
              AND schedules.id = ?
        """, (student_id, schedule_id))
        record = cursor.fetchone()

        if not record:
            return False, "Student is not enrolled in this class."

        if str(record[6]).upper() != "ACTIVE":
            return False, "Student account is inactive."

        if str(record[3]).strip().upper() != str(record[10]).strip().upper():
            return False, "Course does not match."

        if str(record[4]).strip().upper() != str(record[11]).strip().upper():
            return False, "Year level does not match."

        if str(record[5]).strip().upper() != str(record[12]).strip().upper():
            return False, "Section does not match."

        cursor.execute("""
            SELECT id, attendance_time, status
            FROM attendance
            WHERE student_id = ?
              AND schedule_id = ?
              AND attendance_date = ?
        """, (student_id, schedule_id, attendance_date))
        existing = cursor.fetchone()

        if existing:
            return False, (
                "Attendance already recorded.\n"
                "Time: " + str(existing[1])
                + "\nStatus: " + str(existing[2])
            )

        status = get_attendance_status(record[13], attendance_time)

        cursor.execute("""
            INSERT INTO attendance
            (
                student_id, schedule_id, attendance_date,
                attendance_time, status, method
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            student_id, schedule_id, attendance_date,
            attendance_time, status, str(method).upper()
        ))
        connection.commit()
        return True, status

    except sqlite3.IntegrityError:
        connection.rollback()
        return False, "Attendance already recorded for this student and class today."
    except Exception as error:
        connection.rollback()
        return False, str(error)
    finally:
        connection.close()


# ============================================================
# CONTINUOUS QR ATTENDANCE
# ============================================================

def attendance_qr_page(app, teacher, selected_schedule):
    schedule_id = selected_schedule[0]
    schedule_subject = selected_schedule[1]
    schedule_course = selected_schedule[2]
    schedule_year = selected_schedule[3]
    schedule_section = selected_schedule[4]
    schedule_day = selected_schedule[5]
    schedule_start = selected_schedule[6]
    schedule_end = selected_schedule[7]

    clear_screen(app)
    create_top_bar(
        app, app, True,
        lambda: teacher_attendance_page(app, teacher)
    )
    create_page_title(
        app, "QR ATTENDANCE",
        "Continuous QR verification. The scanner stays open until you close it."
    )

    panel = ctk.CTkFrame(
        app, fg_color=CARD, corner_radius=18,
        border_width=1, border_color=BORDER
    )
    panel.pack(fill="both", expand=True, padx=55, pady=10)

    ctk.CTkLabel(
        panel,
        text=(
            schedule_subject + " | " + schedule_course
            + " | " + schedule_year + " | Section " + schedule_section
            + "\n" + schedule_day + " "
            + format_time_12h(schedule_start)
            + " - " + format_time_12h(schedule_end)
        ),
        font=("Arial", 12, "bold"), text_color=PURPLE,
        justify="center"
    ).pack(pady=(20, 10))

    result_label = ctk.CTkLabel(
        panel, text="READY — OPEN THE QR SCANNER",
        font=("Arial", 18, "bold"), text_color=TEXT
    )
    result_label.pack(pady=8)

    details_label = ctk.CTkLabel(
        panel, text="No student verified yet.",
        font=("Arial", 11), text_color=MUTED,
        justify="center", wraplength=700
    )
    details_label.pack(pady=8)

    token_entry = create_input(panel, "QR Token (manual fallback)")
    token_entry.pack(fill="x", padx=100, pady=8)

    def validate_token(token):
        token = str(token or "").strip()
        if not token:
            return False, "NOT VERIFIED", "QR token is empty.", ERROR

        connection = get_connection()
        cursor = connection.cursor()
        try:
            cursor.execute("""
                SELECT
                    qr_codes.student_id,
                    qr_codes.schedule_id,
                    qr_codes.token,
                    qr_codes.created_at,
                    students.school_id,
                    students.name,
                    students.course,
                    students.year,
                    students.section,
                    schedules.subject,
                    schedules.teacher_id,
                    teachers.name,
                    schedules.start_time
                FROM qr_codes
                INNER JOIN students ON qr_codes.student_id = students.id
                INNER JOIN schedules ON qr_codes.schedule_id = schedules.id
                INNER JOIN teachers ON schedules.teacher_id = teachers.id
                WHERE qr_codes.token = ?
            """, (token,))
            row = cursor.fetchone()
        finally:
            connection.close()

        if not row:
            return False, "NOT VERIFIED", "QR token not found.", ERROR

        if row[1] != schedule_id:
            return False, "NOT VERIFIED", "Wrong class QR.", ERROR

        if row[10] != teacher[0]:
            return False, "NOT VERIFIED", "Wrong teacher/TC.", ERROR

        checks = [
            (row[6], schedule_course, "Course mismatch."),
            (row[7], schedule_year, "Year mismatch."),
            (row[8], schedule_section, "Section mismatch."),
            (row[9], schedule_subject, "Subject mismatch.")
        ]
        for actual, expected, message in checks:
            if str(actual).strip().upper() != str(expected).strip().upper():
                return False, "NOT VERIFIED", message, ERROR

        # QR expiration is based on its stored creation time.
        try:
            created = datetime.strptime(
                str(row[3]),
                "%Y-%m-%d %H:%M:%S"
            )
            age_seconds = (datetime.now() - created).total_seconds()
            if age_seconds > QR_EXPIRATION_HOURS * 3600:
                return False, "NOT VERIFIED", "QR code has expired. Generate a new QR.", ERROR
        except Exception:
            # Old records without a parseable timestamp remain
            # usable rather than being silently destroyed.
            pass

        connection = get_connection()
        cursor = connection.cursor()
        try:
            cursor.execute("""
                SELECT id
                FROM student_classes
                WHERE student_id = ?
                  AND schedule_id = ?
            """, (row[0], schedule_id))
            enrolled = cursor.fetchone()
        finally:
            connection.close()

        if not enrolled:
            return False, "NOT VERIFIED", "Student is not enrolled in this class.", ERROR

        success, status = record_attendance(
            row[0], schedule_id, "QR"
        )

        if not success:
            if str(status).lower().startswith("attendance already recorded"):
                return False, "ALREADY VERIFIED", status, WARNING
            return False, "NOT VERIFIED", status, ERROR

        detail = (
            "Student: " + str(row[5])
            + "\nSchool ID: " + str(row[4])
            + "\nCourse: " + str(row[6])
            + " | Year: " + str(row[7])
            + " | Section: " + str(row[8])
            + "\nSubject: " + str(row[9])
            + "\nStatus: " + str(status)
            + " | Method: QR"
        )
        return True, "VERIFIED", detail, SUCCESS

    def verify_manual():
        token = token_entry.get().strip()
        ok, title, detail, color = validate_token(token)
        result_label.configure(text=title, text_color=color)
        details_label.configure(text=detail, text_color=color)
        if ok:
            token_entry.delete(0, "end")

    def scan_qr_camera():
        try:
            import cv2
        except ImportError as error:
            result_label.configure(text="NOT VERIFIED", text_color=ERROR)
            details_label.configure(text="OpenCV is not installed.\n" + str(error), text_color=ERROR)
            return

        camera = cv2.VideoCapture(0)
        if not camera.isOpened():
            result_label.configure(text="NOT VERIFIED", text_color=ERROR)
            details_label.configure(text="Camera unavailable.", text_color=ERROR)
            return

        detector = cv2.QRCodeDetector()
        window_name = "AttendX QR Attendance — Continuous"
        cv2.namedWindow(window_name)
        cancel = {"value": False}
        last_token = ""
        last_scan_time = 0.0
        overlay_text = "READY — SCAN STUDENT QR"
        overlay_color = (0, 255, 0)
        overlay_until = 0.0

        def mouse(event, x, y, flags, param):
            if event == cv2.EVENT_LBUTTONDOWN:
                height, width = param
                if width - 180 <= x <= width - 20 and height - 75 <= y <= height - 20:
                    cancel["value"] = True

        import time as _time

        while True:
            success, frame = camera.read()
            if not success:
                overlay_text = "CAMERA READ ERROR"
                overlay_color = (0, 0, 255)
                break

            data, points, _ = detector.detectAndDecode(frame)
            height, width = frame.shape[:2]

            if points is not None:
                points = points.astype(int)
                for i in range(len(points[0])):
                    pt1 = tuple(points[0][i])
                    pt2 = tuple(points[0][(i + 1) % len(points[0])])
                    cv2.line(frame, pt1, pt2, (0, 255, 0), 3)

            now_seconds = _time.time()
            if data:
                token = data.strip()
                if token and (token != last_token or now_seconds - last_scan_time > 2.5):
                    last_token = token
                    last_scan_time = now_seconds
                    ok, title, detail, color = validate_token(token)
                    overlay_text = title
                    overlay_color = (
                        (0, 255, 0) if color == SUCCESS
                        else (0, 165, 255) if color == WARNING
                        else (0, 0, 255)
                    )
                    result_label.configure(text=title, text_color=color)
                    details_label.configure(text=detail, text_color=color)
                    overlay_until = now_seconds + 2.0

            cv2.putText(
                frame, "CONTINUOUS QR ATTENDANCE",
                (20, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.72,
                overlay_color if now_seconds < overlay_until else (0, 255, 0), 2
            )
            cv2.putText(
                frame, overlay_text,
                (20, 72), cv2.FONT_HERSHEY_SIMPLEX, 0.82,
                overlay_color if now_seconds < overlay_until else (0, 255, 0), 2
            )
            cv2.putText(
                frame, "SCAN NEXT STUDENT",
                (20, 108), cv2.FONT_HERSHEY_SIMPLEX, 0.58,
                (255, 255, 255), 2
            )

            cv2.rectangle(
                frame,
                (width - 180, height - 75),
                (width - 20, height - 20),
                (80, 80, 80), -1
            )
            cv2.putText(
                frame, "CLOSE",
                (width - 150, height - 38),
                cv2.FONT_HERSHEY_SIMPLEX, 0.60,
                (255, 255, 255), 2
            )
            cv2.setMouseCallback(window_name, mouse, (height, width))
            cv2.imshow(window_name, frame)

            key = cv2.waitKey(1) & 0xFF
            if cancel["value"] or key in (27, ord("q")):
                break

        camera.release()
        cv2.destroyAllWindows()

    create_button(
        panel, "SCAN QR WITH CAMERA",
        scan_qr_camera, width=260
    ).pack(pady=10)
    create_button(
        panel, "VERIFY TOKEN",
        verify_manual, width=260
    ).pack(pady=10)
    create_button(
        panel, "BACK",
        lambda: teacher_attendance_page(app, teacher),
        width=260, fg_color="#242B40", hover_color="#323B55"
    ).pack(pady=(5, 15))


# ============================================================
# CONTINUOUS FACE ATTENDANCE
# ============================================================

def face_attendance_action(app, teacher, selected_schedule):
    try:
        import cv2
        import face_recognition
    except ImportError as error:
        messagebox.showerror(
            "FACE ATTENDANCE",
            "Required face-recognition packages are not installed.\n\n"
            + str(error)
        )
        return

    schedule_id = selected_schedule[0]
    subject = selected_schedule[1]
    course = selected_schedule[2]
    year = selected_schedule[3]
    section = selected_schedule[4]

    clear_screen(app)
    create_top_bar(
        app, app, True,
        lambda: teacher_attendance_page(app, teacher)
    )
    create_page_title(
        app, "FACE ATTENDANCE",
        "Continuous face verification. The camera remains open for multiple students."
    )

    panel = ctk.CTkFrame(
        app, fg_color=CARD, corner_radius=18,
        border_width=1, border_color=BORDER
    )
    panel.pack(fill="both", expand=True, padx=55, pady=10)

    result_label = ctk.CTkLabel(
        panel, text="READY — START FACE SCANNER",
        font=("Arial", 18, "bold"), text_color=TEXT
    )
    result_label.pack(pady=(25, 8))

    details_label = ctk.CTkLabel(
        panel, text="No student verified yet.",
        font=("Arial", 11), text_color=MUTED,
        justify="center", wraplength=750
    )
    details_label.pack(pady=5)

    def scan_face():
        camera = cv2.VideoCapture(0)
        if not camera.isOpened():
            result_label.configure(text="NOT VERIFIED", text_color=ERROR)
            details_label.configure(text="Camera unavailable.", text_color=ERROR)
            return

        window_name = "AttendX FACE Attendance — Continuous"
        cv2.namedWindow(window_name)

        import time as _time
        last_student_id = None
        last_scan_time = 0.0
        frame_index = 0
        overlay_text = "LOOK AT CAMERA"
        overlay_color = (0, 255, 0)
        overlay_until = 0.0
        cancel = {"value": False}

        def mouse(event, x, y, flags, param):
            if event == cv2.EVENT_LBUTTONDOWN:
                height, width = param
                if width - 180 <= x <= width - 20 and height - 75 <= y <= height - 20:
                    cancel["value"] = True

        while True:
            success, frame = camera.read()
            if not success:
                overlay_text = "CAMERA READ ERROR"
                overlay_color = (0, 0, 255)
                break

            frame_index += 1
            small = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
            rgb_small = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)

            face_locations = []
            face_encodings = []

            if frame_index % 3 == 0:
                face_locations = face_recognition.face_locations(
                    rgb_small, model="hog"
                )
                if len(face_locations) == 1:
                    face_encodings = face_recognition.face_encodings(
                        rgb_small, face_locations
                    )

            for location in face_locations:
                top, right, bottom, left = [int(v * 2) for v in location]
                cv2.rectangle(
                    frame, (left, top), (right, bottom),
                    (0, 255, 0), 2
                )

            now_seconds = _time.time()

            if len(face_locations) > 1:
                overlay_text = "ONLY ONE FACE ALLOWED"
                overlay_color = (0, 0, 255)

            elif len(face_locations) == 0:
                overlay_text = "LOOK AT CAMERA"
                overlay_color = (255, 200, 0)

            elif len(face_encodings) == 1:
                result = find_student_by_face(face_encodings[0])

                if not result.get("found"):
                    overlay_text = "NOT VERIFIED"
                    overlay_color = (0, 0, 255)
                    details = result.get(
                        "message",
                        "Face not recognized."
                    )
                    result_label.configure(
                        text="NOT VERIFIED", text_color=ERROR
                    )
                    details_label.configure(
                        text=details, text_color=ERROR
                    )
                    overlay_until = now_seconds + 1.5
                else:
                    student_id = result.get("student_id")
                    distance = result.get("distance")

                    if (
                        student_id != last_student_id
                        or now_seconds - last_scan_time > 3.0
                    ):
                        last_student_id = student_id
                        last_scan_time = now_seconds

                        success_record, attendance_result = record_attendance(
                            student_id,
                            schedule_id,
                            "FACE"
                        )

                        connection = get_connection()
                        cursor = connection.cursor()
                        cursor.execute("""
                            SELECT school_id, name, course, year, section
                            FROM students
                            WHERE id = ?
                        """, (student_id,))
                        student_row = cursor.fetchone()
                        connection.close()

                        if success_record:
                            overlay_text = "VERIFIED"
                            overlay_color = (0, 255, 0)
                            detail = (
                                "Student: " + str(student_row[1])
                                + "\nStudent ID: " + str(student_row[0])
                                + "\nCourse: " + str(student_row[2])
                                + " | Year: " + str(student_row[3])
                                + " | Section: " + str(student_row[4])
                                + "\nSubject: " + str(subject)
                                + "\nStatus: " + str(attendance_result)
                                + " | Method: FACE"
                            )
                            result_label.configure(
                                text="VERIFIED", text_color=SUCCESS
                            )
                            details_label.configure(
                                text=detail, text_color=SUCCESS
                            )
                        else:
                            if str(attendance_result).lower().startswith("attendance already recorded"):
                                overlay_text = "ALREADY VERIFIED"
                                overlay_color = (0, 165, 255)
                                result_label.configure(
                                    text="ALREADY VERIFIED",
                                    text_color=WARNING
                                )
                            else:
                                overlay_text = "NOT VERIFIED"
                                overlay_color = (0, 0, 255)
                                result_label.configure(
                                    text="NOT VERIFIED",
                                    text_color=ERROR
                                )
                            details_label.configure(
                                text=str(attendance_result),
                                text_color=WARNING if "already" in str(attendance_result).lower() else ERROR
                            )
                        overlay_until = now_seconds + 2.0

            cv2.putText(
                frame, "CONTINUOUS FACE ATTENDANCE",
                (20, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.72,
                overlay_color, 2
            )
            cv2.putText(
                frame, overlay_text,
                (20, 72), cv2.FONT_HERSHEY_SIMPLEX, 0.82,
                overlay_color, 2
            )
            cv2.putText(
                frame,
                "NEXT STUDENT CAN SCAN",
                (20, 108), cv2.FONT_HERSHEY_SIMPLEX, 0.58,
                (255, 255, 255), 2
            )

            height, width = frame.shape[:2]
            cv2.rectangle(
                frame,
                (width - 180, height - 75),
                (width - 20, height - 20),
                (80, 80, 80), -1
            )
            cv2.putText(
                frame, "CLOSE",
                (width - 150, height - 38),
                cv2.FONT_HERSHEY_SIMPLEX, 0.60,
                (255, 255, 255), 2
            )
            cv2.setMouseCallback(window_name, mouse, (height, width))
            cv2.imshow(window_name, frame)

            key = cv2.waitKey(1) & 0xFF
            if cancel["value"] or key in (27, ord("q")):
                break

        camera.release()
        cv2.destroyAllWindows()

    create_button(
        panel, "START CONTINUOUS FACE SCANNER",
        scan_face, width=300
    ).pack(pady=12)
    create_button(
        panel, "BACK",
        lambda: teacher_attendance_page(app, teacher),
        width=260, fg_color="#242B40", hover_color="#323B55"
    ).pack(pady=(5, 20))


# ============================================================
# FINGERPRINT STATUS — NO FAKE SUCCESS
# ============================================================

def fingerprint_status_page(app, teacher):
    clear_screen(app)
    create_top_bar(
        app, app, True,
        lambda: tc_dashboard(app, teacher) if CURRENT_USER_ROLE == "tc"
        else teacher_dashboard(app, teacher)
    )
    create_page_title(
        app, "FINGERPRINT / DEVICE",
        "The interface reports the real hardware state only."
    )

    card = ctk.CTkFrame(
        app, fg_color=CARD, corner_radius=18,
        border_width=1, border_color=BORDER
    )
    card.pack(expand=True, padx=100, pady=30, fill="x")

    fingerprint = FingerprintSystem()
    try:
        status = fingerprint.get_device_status()
    except Exception as error:
        status = {"available": False, "devices": []}
        error_text = str(error)
    else:
        error_text = ""

    if status.get("available"):
        state = "DEVICE CONNECTED"
        color = SUCCESS
        details = "\n".join(
            "- " + str(device)
            for device in status.get("devices", [])
        )
    else:
        state = "DEVICE NOT DETECTED"
        color = WARNING
        details = (
            "No supported fingerprint/biometric device was detected.\n"
            "Registration and verification remain unavailable until hardware is connected."
        )
        if error_text:
            details += "\n\n" + error_text

    ctk.CTkLabel(
        card, text=state,
        font=("Arial", 22, "bold"), text_color=color
    ).pack(pady=(35, 15))
    ctk.CTkLabel(
        card, text=details,
        font=("Arial", 11), text_color=TEXT,
        justify="center", wraplength=700
    ).pack(pady=(0, 20))

    create_button(
        card, "REFRESH DEVICE STATUS",
        lambda: fingerprint_status_page(app, teacher),
        width=250
    ).pack(pady=8)
    create_button(
        card, "BACK",
        lambda: tc_dashboard(app, teacher) if CURRENT_USER_ROLE == "tc"
        else teacher_dashboard(app, teacher),
        width=250, fg_color="#242B40", hover_color="#323B55"
    ).pack(pady=(8, 30))


def fingerprint_register_action(student):
    try:
        fingerprint = FingerprintSystem()
        status = fingerprint.get_device_status()
        if not status.get("available"):
            messagebox.showwarning(
                "Fingerprint Registration",
                "DEVICE NOT DETECTED.\n\n"
                "No fingerprint registration was performed."
            )
            return
        success, message = fingerprint.register_fingerprint(student[0])
        if success:
            messagebox.showinfo(
                "Fingerprint Registration",
                "Fingerprint registration completed."
            )
        else:
            messagebox.showwarning(
                "Fingerprint Registration",
                "Registration was not completed.\n\n" + str(message)
            )
    except Exception as error:
        messagebox.showerror(
            "Fingerprint Registration",
            "Unable to check the fingerprint device.\n\n" + str(error)
        )


def fingerprint_attendance_action(app, teacher, selected_schedule):
    try:
        fingerprint = FingerprintSystem()
        status = fingerprint.get_device_status()
        if not status.get("available"):
            messagebox.showwarning(
                "Fingerprint Attendance",
                "DEVICE NOT DETECTED.\n\n"
                "No fingerprint attendance was recorded."
            )
            return

        success, message = fingerprint.verify_fingerprint(None)
        if success:
            messagebox.showinfo(
                "Fingerprint Attendance",
                "Fingerprint verification completed."
            )
        else:
            messagebox.showwarning(
                "Fingerprint Attendance",
                "Verification was not completed.\n\n" + str(message)
            )
    except Exception as error:
        messagebox.showerror(
            "Fingerprint Attendance",
            "Unable to check the fingerprint device.\n\n" + str(error)
        )


# ============================================================
# REPORTS
# ============================================================

def reports_page(app, teacher):
    clear_screen(app)
    create_top_bar(
        app, app, True,
        lambda: tc_dashboard(app, teacher) if CURRENT_USER_ROLE == "tc"
        else teacher_dashboard(app, teacher)
    )
    create_page_title(
        app, "REPORTS",
        "Export actual AttendX attendance records."
    )

    card = ctk.CTkFrame(
        app, fg_color=CARD, corner_radius=18,
        border_width=1, border_color=BORDER
    )
    card.pack(expand=True, padx=100, pady=30, fill="x")

    ctk.CTkLabel(
        card,
        text="ATTENDANCE REPORT EXPORT",
        font=("Arial", 20, "bold"), text_color=WHITE
    ).pack(pady=(30, 8))

    ctk.CTkLabel(
        card,
        text="Exports are generated directly from attendance.db.",
        font=("Arial", 11), text_color=MUTED
    ).pack(pady=(0, 20))

    def get_rows():
        connection = get_connection()
        cursor = connection.cursor()
        try:
            cursor.execute("""
                SELECT
                    attendance.attendance_date,
                    attendance.attendance_time,
                    students.name,
                    students.school_id,
                    students.course,
                    students.year,
                    students.section,
                    schedules.subject,
                    teachers.name,
                    COALESCE(teachers.role, 'TEACHER'),
                    attendance.method,
                    attendance.status
                FROM attendance
                INNER JOIN students ON attendance.student_id = students.id
                INNER JOIN schedules ON attendance.schedule_id = schedules.id
                INNER JOIN teachers ON schedules.teacher_id = teachers.id
                ORDER BY attendance.attendance_date DESC,
                         attendance.attendance_time DESC
            """)
            return cursor.fetchall()
        finally:
            connection.close()

    headers = [
        "Date", "Time", "Student", "Student ID",
        "Course", "Year", "Section", "Subject",
        "Teacher/TC", "Role", "Method", "Status"
    ]

    def export_csv():
        import csv
        destination = filedialog.asksaveasfilename(
            parent=app,
            title="Export CSV",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")]
        )
        if not destination:
            return
        rows = get_rows()
        try:
            with open(destination, "w", newline="", encoding="utf-8-sig") as file:
                writer = csv.writer(file)
                writer.writerow(headers)
                writer.writerows(rows)
            messagebox.showinfo(
                "CSV Export",
                "CSV report exported successfully."
            )
        except Exception as error:
            messagebox.showerror("CSV Export", str(error))

    def export_xlsx():
        destination = filedialog.asksaveasfilename(
            parent=app,
            title="Export Excel",
            defaultextension=".xlsx",
            filetypes=[("Excel Workbook", "*.xlsx")]
        )
        if not destination:
            return
        try:
            from openpyxl import Workbook
            workbook = Workbook()
            sheet = workbook.active
            sheet.title = "Attendance"
            sheet.append(headers)
            for row in get_rows():
                sheet.append(list(row))
            workbook.save(destination)
            messagebox.showinfo(
                "Excel Export",
                "Excel report exported successfully."
            )
        except ImportError:
            messagebox.showerror(
                "Excel Export",
                "openpyxl is not installed. Install it to export XLSX reports."
            )
        except Exception as error:
            messagebox.showerror("Excel Export", str(error))

    def export_pdf():
        destination = filedialog.asksaveasfilename(
            parent=app,
            title="Export PDF",
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")]
        )
        if not destination:
            return
        try:
            from reportlab.lib import colors as pdf_colors
            from reportlab.lib.pagesizes import landscape, letter
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
            document = SimpleDocTemplate(
                destination, pagesize=landscape(letter)
            )
            table_data = [headers] + [list(row) for row in get_rows()]
            table = Table(table_data, repeatRows=1)
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), pdf_colors.HexColor("#7C5CFC")),
                ("TEXTCOLOR", (0, 0), (-1, 0), pdf_colors.white),
                ("GRID", (0, 0), (-1, -1), 0.4, pdf_colors.grey),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE")
            ]))
            document.build([table])
            messagebox.showinfo(
                "PDF Export",
                "PDF report exported successfully."
            )
        except ImportError:
            messagebox.showerror(
                "PDF Export",
                "reportlab is not installed. Install it to export PDF reports."
            )
        except Exception as error:
            messagebox.showerror("PDF Export", str(error))

    create_button(card, "EXPORT CSV", export_csv, width=260).pack(pady=8)
    create_button(card, "EXPORT EXCEL (.XLSX)", export_xlsx, width=260).pack(pady=8)
    create_button(card, "EXPORT PDF / PRINT", export_pdf, width=260).pack(pady=8)
    create_button(
        card, "BACK",
        lambda: tc_dashboard(app, teacher) if CURRENT_USER_ROLE == "tc"
        else teacher_dashboard(app, teacher),
        width=260, fg_color="#242B40", hover_color="#323B55"
    ).pack(pady=(8, 30))


# ============================================================
# BACKUP / RESTORE
# ============================================================

def backup_restore_page(app, teacher):
    clear_screen(app)
    create_top_bar(
        app, app, True,
        lambda: tc_dashboard(app, teacher) if CURRENT_USER_ROLE == "tc"
        else teacher_dashboard(app, teacher)
    )
    create_page_title(
        app, "BACKUP / RESTORE",
        "Protect the active AttendX database before restoring."
    )

    card = ctk.CTkFrame(
        app, fg_color=CARD, corner_radius=18,
        border_width=1, border_color=BORDER
    )
    card.pack(expand=True, padx=100, pady=30, fill="x")

    def backup():
        destination = filedialog.asksaveasfilename(
            parent=app,
            title="Backup AttendX Database",
            initialfile="attendance_backup.db",
            defaultextension=".db",
            filetypes=[("SQLite Database", "*.db")]
        )
        if not destination:
            return
        try:
            source = os.path.abspath(DB_FILE)
            shutil.copy2(source, destination)
            messagebox.showinfo(
                "Backup Complete",
                "Database backup completed successfully."
            )
        except Exception as error:
            messagebox.showerror(
                "Backup Failed",
                "Database backup failed.\n\n" + str(error)
            )

    def restore():
        source = filedialog.askopenfilename(
            parent=app,
            title="Select AttendX Database Backup",
            filetypes=[("SQLite Database", "*.db"), ("All Files", "*.*")]
        )
        if not source:
            return

        answer = messagebox.askyesno(
            "Confirm Restore",
            "Restore this database and replace the active attendance.db?\n\n"
            "Make sure you have a current backup first."
        )
        if not answer:
            return

        try:
            # Validate that the selected file is an SQLite database
            # before touching the active database.
            test = sqlite3.connect(source)
            test.execute("SELECT name FROM sqlite_master LIMIT 1")
            test.close()

            active = os.path.abspath(DB_FILE)
            temporary = active + ".restore_tmp"
            shutil.copy2(source, temporary)
            os.replace(temporary, active)

            messagebox.showinfo(
                "Restore Complete",
                "Database restored successfully.\n\n"
                "Restart AttendX to reload all restored records."
            )
        except Exception as error:
            try:
                if os.path.exists(active + ".restore_tmp"):
                    os.remove(active + ".restore_tmp")
            except Exception:
                pass
            messagebox.showerror(
                "Restore Failed",
                "Database restore failed.\n\n" + str(error)
            )

    ctk.CTkLabel(
        card, text="DATABASE SAFETY",
        font=("Arial", 20, "bold"), text_color=WHITE
    ).pack(pady=(35, 8))
    ctk.CTkLabel(
        card,
        text="Backup copies the actual attendance.db. Restore requires confirmation.",
        font=("Arial", 11), text_color=MUTED
    ).pack(pady=(0, 20))
    create_button(card, "BACKUP DATABASE", backup, width=280).pack(pady=8)
    create_button(card, "RESTORE DATABASE", restore, width=280).pack(pady=8)
    create_button(
        card, "BACK",
        lambda: tc_dashboard(app, teacher) if CURRENT_USER_ROLE == "tc"
        else teacher_dashboard(app, teacher),
        width=280, fg_color="#242B40", hover_color="#323B55"
    ).pack(pady=(8, 30))


# ============================================================
# CONTROLLED SCHEDULE MANAGEMENT
# ============================================================

def teacher_add_schedule_page(app, teacher):
    clear_screen(app)
    create_top_bar(
        app, app, True,
        lambda: tc_dashboard(app, teacher) if CURRENT_USER_ROLE == "tc"
        else teacher_dashboard(app, teacher)
    )
    create_page_title(
        app, "ADD SCHEDULE",
        "Create a validated class schedule."
    )

    form = ctk.CTkScrollableFrame(
        app, width=700, height=650,
        fg_color=CARD, corner_radius=18,
        border_width=1, border_color=BORDER
    )
    form.pack(fill="both", expand=True, padx=80, pady=(0, 15))

    ctk.CTkLabel(
        form, text="CLASS SCHEDULE",
        font=("Arial", 22, "bold"), text_color=WHITE
    ).pack(pady=(20, 10))

    ctk.CTkLabel(
        form, text="Assigned to: " + str(teacher[2])
        + " (" + ("TC" if CURRENT_USER_ROLE == "tc" else "TEACHER") + ")",
        font=("Arial", 10, "bold"), text_color=PURPLE
    ).pack(pady=(0, 12))

    ctk.CTkLabel(form, text="Course", font=("Arial", 10, "bold"), text_color=MUTED).pack(anchor="w")
    course = _make_combo(form, _get_course_values())
    course.pack(fill="x", pady=6)

    ctk.CTkLabel(form, text="Subject", font=("Arial", 10, "bold"), text_color=MUTED).pack(anchor="w")
    subject_values = []
    subject_lookup = {}
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("""
        SELECT subject_code, subject_name
        FROM subjects
        WHERE UPPER(COALESCE(status, 'ACTIVE')) = 'ACTIVE'
        ORDER BY subject_code
    """)
    for row in cursor.fetchall():
        label = row[0] + " | " + row[1]
        subject_values.append(label)
        subject_lookup[label] = row
    connection.close()

    if not subject_values:
        subject_values = ["CREATE SUBJECT FIRST"]
        subject_lookup["CREATE SUBJECT FIRST"] = ("", "")

    subject_box = _make_combo(form, subject_values)
    subject_box.pack(fill="x", pady=6)

    ctk.CTkLabel(form, text="Year", font=("Arial", 10, "bold"), text_color=MUTED).pack(anchor="w")
    year = _make_combo(form, ["1ST", "2ND", "3RD", "4TH"], "1ST")
    year.pack(fill="x", pady=6)

    ctk.CTkLabel(form, text="Section", font=("Arial", 10, "bold"), text_color=MUTED).pack(anchor="w")
    section = _make_combo(form, _get_section_values(course.get(), year.get()), "A")
    section.pack(fill="x", pady=6)

    def refresh_sections(_value=None):
        values = _get_section_values(course.get(), year.get())
        section.configure(values=values)
        if section.get() not in values:
            section.set(values[0])

    course.configure(command=refresh_sections)
    year.configure(command=refresh_sections)

    day = _make_combo(
        form,
        ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
        "Monday"
    )
    day.pack(fill="x", pady=6)

    _, start_hour, start_minute, start_period = create_time_selector(
        form, "Start Time", "7", "00", "AM"
    )
    _, end_hour, end_minute, end_period = create_time_selector(
        form, "End Time", "8", "00", "AM"
    )

    def save_schedule():
        course_value = _normalize_text(course.get()).upper()
        year_value = _normalize_text(year.get()).upper()
        section_value = _normalize_text(section.get()).upper()
        day_value = _normalize_text(day.get())
        selected_subject = subject_lookup.get(subject_box.get())
        if not selected_subject or not selected_subject[0]:
            messagebox.showerror(
                "Schedule Error",
                "Select a valid centralized subject first."
            )
            return

        subject_code = selected_subject[0]
        subject_name = selected_subject[1]
        start_value = to_24_hour(
            start_hour.get(), start_minute.get(), start_period.get()
        )
        end_value = to_24_hour(
            end_hour.get(), end_minute.get(), end_period.get()
        )

        start_minutes = convert_time(start_value)
        end_minutes = convert_time(end_value)

        if not course_value or not year_value or not section_value or not day_value:
            messagebox.showerror(
                "Schedule Error",
                "Course, Year, Section and Day are required."
            )
            return

        if start_minutes is None or end_minutes is None:
            messagebox.showerror(
                "Invalid Time",
                "Please select valid start and end times."
            )
            return

        if end_minutes <= start_minutes:
            messagebox.showerror(
                "Invalid Time",
                "End Time must be later than Start Time."
            )
            return

        connection = get_connection()
        cursor = connection.cursor()
        try:
            # Exact duplicate prevention.
            cursor.execute("""
                SELECT id
                FROM schedules
                WHERE teacher_id = ?
                  AND UPPER(TRIM(course)) = UPPER(TRIM(?))
                  AND UPPER(TRIM(subject)) = UPPER(TRIM(?))
                  AND UPPER(TRIM(section)) = UPPER(TRIM(?))
                  AND UPPER(TRIM(year)) = UPPER(TRIM(?))
                  AND day = ?
                  AND start_time = ?
                  AND end_time = ?
            """, (
                teacher[0], course_value, subject_name, section_value,
                year_value, day_value, start_value, end_value
            ))
            if cursor.fetchone():
                messagebox.showerror(
                    "Duplicate Schedule",
                    "This exact schedule already exists."
                )
                return

            # Overlap prevention for the same Teacher/TC and day.
            cursor.execute("""
                SELECT start_time, end_time
                FROM schedules
                WHERE teacher_id = ? AND day = ?
            """, (teacher[0], day_value))
            for old_start, old_end in cursor.fetchall():
                old_start_minutes = convert_time(old_start)
                old_end_minutes = convert_time(old_end)
                if (
                    old_start_minutes is not None
                    and old_end_minutes is not None
                    and start_minutes < old_end_minutes
                    and end_minutes > old_start_minutes
                ):
                    messagebox.showerror(
                        "Schedule Conflict",
                        "This schedule overlaps another schedule for the same Teacher/TC and day."
                    )
                    return

            cursor.execute("""
                INSERT INTO schedules
                (
                    teacher_id, course, subject, section, year,
                    day, start_time, end_time, subject_code
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                teacher[0], course_value, subject_name, section_value,
                year_value, day_value, start_value, end_value, subject_code
            ))
            connection.commit()
        except sqlite3.IntegrityError as error:
            connection.rollback()
            messagebox.showerror("Schedule Error", str(error))
            return
        except Exception as error:
            connection.rollback()
            messagebox.showerror("Schedule Error", str(error))
            return
        finally:
            connection.close()

        messagebox.showinfo("Schedule Added", "Class schedule successfully added.")
        tc_dashboard(app, teacher) if CURRENT_USER_ROLE == "tc" else teacher_dashboard(app, teacher)

    create_button(form, "SAVE SCHEDULE", save_schedule, width=300).pack(pady=(18, 8))
    create_button(
        form, "CANCEL",
        lambda: tc_dashboard(app, teacher) if CURRENT_USER_ROLE == "tc"
        else teacher_dashboard(app, teacher),
        width=300, fg_color="#242B40", hover_color="#323B55"
    ).pack(pady=(0, 20))


# ============================================================
# SAFE TEACHER DASHBOARD NAVIGATION PATCH
# ============================================================


if __name__ == "__main__":
    run_intro()
    main()