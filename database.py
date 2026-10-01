import sqlite3
import os
from datetime import datetime


# ============================================================
# DATABASE CONFIGURATION
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ============================================================
# OFFICIAL ATTENDX DATABASE
# ============================================================

DB_FILE = os.path.join(
    BASE_DIR,
    "attendance.db"
)


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_connection():
    connection = sqlite3.connect(DB_FILE)

    connection.execute(
        "PRAGMA foreign_keys = ON"
    )

    return connection


# ============================================================
# CURRENT DATETIME
# ============================================================

def get_current_datetime():
    return datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )


# ============================================================
# DATABASE TABLE CREATION
# ============================================================

def create_database():

    connection = get_connection()
    cursor = connection.cursor()

    # ========================================================
    # STUDENTS
    # ========================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            school_id TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            name TEXT NOT NULL,
            course TEXT NOT NULL,
            year TEXT NOT NULL,
            section TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'ACTIVE',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ========================================================
    # TEACHERS
    # ========================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS teachers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            teacher_id TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            name TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'ACTIVE',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ========================================================
    # SCHEDULES
    # ========================================================

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
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (teacher_id)
                REFERENCES teachers(id)
                ON DELETE CASCADE
        )
    """)

    # ========================================================
    # STUDENT CLASSES
    # ========================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS student_classes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            schedule_id INTEGER NOT NULL,
            joined_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

            UNIQUE(
                student_id,
                schedule_id
            ),

            FOREIGN KEY (student_id)
                REFERENCES students(id)
                ON DELETE CASCADE,

            FOREIGN KEY (schedule_id)
                REFERENCES schedules(id)
                ON DELETE CASCADE
        )
    """)

    # ========================================================
    # QR CODES
    # ========================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS qr_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            schedule_id INTEGER NOT NULL,
            token TEXT UNIQUE NOT NULL,
            qr_file TEXT,
            created_at TEXT NOT NULL,

            UNIQUE(
                student_id,
                schedule_id
            ),

            FOREIGN KEY (student_id)
                REFERENCES students(id)
                ON DELETE CASCADE,

            FOREIGN KEY (schedule_id)
                REFERENCES schedules(id)
                ON DELETE CASCADE
        )
    """)

    # ========================================================
    # ATTENDANCE
    # ========================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            schedule_id INTEGER NOT NULL,
            attendance_date TEXT NOT NULL,
            attendance_time TEXT NOT NULL,
            status TEXT NOT NULL,
            method TEXT NOT NULL,

            UNIQUE(
                student_id,
                schedule_id,
                attendance_date
            ),

            FOREIGN KEY (student_id)
                REFERENCES students(id)
                ON DELETE CASCADE,

            FOREIGN KEY (schedule_id)
                REFERENCES schedules(id)
                ON DELETE CASCADE
        )
    """)

    # ========================================================
    # ATTENDANCE SESSIONS
    # ========================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            schedule_id INTEGER NOT NULL,
            teacher_id INTEGER NOT NULL,
            session_token TEXT UNIQUE NOT NULL,
            session_date TEXT NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'ACTIVE',

            FOREIGN KEY (schedule_id)
                REFERENCES schedules(id)
                ON DELETE CASCADE,

            FOREIGN KEY (teacher_id)
                REFERENCES teachers(id)
                ON DELETE CASCADE
        )
    """)

    # ========================================================
    # FACE DATA
    # ========================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS face_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            encoding_file TEXT NOT NULL,
            registered_at TEXT NOT NULL,

            FOREIGN KEY (student_id)
                REFERENCES students(id)
                ON DELETE CASCADE
        )
    """)

    # ========================================================
    # FINGERPRINTS
    # ========================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fingerprints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            fingerprint_id INTEGER NOT NULL,
            finger_name TEXT,
            created_at TEXT NOT NULL,

            UNIQUE(
                student_id,
                fingerprint_id
            ),

            FOREIGN KEY (student_id)
                REFERENCES students(id)
                ON DELETE CASCADE
        )
    """)

    # ========================================================
    # LOGIN HISTORY
    # ========================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS login_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL,
            account_id INTEGER NOT NULL,
            account_number TEXT NOT NULL,
            name TEXT NOT NULL,
            course TEXT,
            year TEXT,
            section TEXT,
            login_date TEXT NOT NULL,
            login_time TEXT NOT NULL
        )
    """)

    # ========================================================
    # AUDIT LOGS
    # ========================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_role TEXT NOT NULL,
            account_id INTEGER,
            action TEXT NOT NULL,
            details TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)

    connection.commit()

    # ========================================================
    # SAFE UPGRADE OF OLD EXISTING TABLES
    # ========================================================

    add_missing_column(
        cursor,
        "students",
        "status",
        "TEXT NOT NULL DEFAULT 'ACTIVE'"
    )

    add_missing_column(
        cursor,
        "students",
        "created_at",
        "TEXT NOT NULL DEFAULT ''"
    )

    add_missing_column(
        cursor,
        "students",
        "updated_at",
        "TEXT NOT NULL DEFAULT ''"
    )

    add_missing_column(
        cursor,
        "teachers",
        "status",
        "TEXT NOT NULL DEFAULT 'ACTIVE'"
    )

    add_missing_column(
        cursor,
        "teachers",
        "created_at",
        "TEXT NOT NULL DEFAULT ''"
    )

    add_missing_column(
        cursor,
        "teachers",
        "updated_at",
        "TEXT NOT NULL DEFAULT ''"
    )

    add_missing_column(
        cursor,
        "schedules",
        "created_at",
        "TEXT NOT NULL DEFAULT ''"
    )

    add_missing_column(
        cursor,
        "schedules",
        "updated_at",
        "TEXT NOT NULL DEFAULT ''"
    )

    add_missing_column(
        cursor,
        "student_classes",
        "joined_at",
        "TEXT NOT NULL DEFAULT ''"
    )

    # ========================================================
    # FILL OLD ROW TIMESTAMPS
    # ========================================================

    now = get_current_datetime()

    cursor.execute("""
        UPDATE students
        SET created_at = ?
        WHERE created_at IS NULL
           OR created_at = ''
    """, (now,))

    cursor.execute("""
        UPDATE students
        SET updated_at = ?
        WHERE updated_at IS NULL
           OR updated_at = ''
    """, (now,))

    cursor.execute("""
        UPDATE teachers
        SET created_at = ?
        WHERE created_at IS NULL
           OR created_at = ''
    """, (now,))

    cursor.execute("""
        UPDATE teachers
        SET updated_at = ?
        WHERE updated_at IS NULL
           OR updated_at = ''
    """, (now,))

    cursor.execute("""
        UPDATE schedules
        SET created_at = ?
        WHERE created_at IS NULL
           OR created_at = ''
    """, (now,))

    cursor.execute("""
        UPDATE schedules
        SET updated_at = ?
        WHERE updated_at IS NULL
           OR updated_at = ''
    """, (now,))

    cursor.execute("""
        UPDATE student_classes
        SET joined_at = ?
        WHERE joined_at IS NULL
           OR joined_at = ''
    """, (now,))

    # ========================================================
    # INDEXES
    # ========================================================

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_students_school_id
        ON students(school_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_students_course_year_section
        ON students(course, year, section)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_teachers_teacher_id
        ON teachers(teacher_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_schedules_teacher
        ON schedules(teacher_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_schedules_matching
        ON schedules(course, year, section)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_student_classes_student
        ON student_classes(student_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_student_classes_schedule
        ON student_classes(schedule_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_qr_token
        ON qr_codes(token)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_attendance_student
        ON attendance(student_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_attendance_schedule
        ON attendance(schedule_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_attendance_date
        ON attendance(attendance_date)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_face_student
        ON face_data(student_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_fingerprint_student
        ON fingerprints(student_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_login_history_account
        ON login_history(role, account_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_audit_logs_account
        ON audit_logs(user_role, account_id)
    """)

    connection.commit()
    connection.close()

    print()
    print("=" * 60)
    print("ATTENDX DATABASE READY")
    print("=" * 60)
    print("Official database:")
    print(DB_FILE)
    print("=" * 60)


# ============================================================
# ADD MISSING COLUMN - SQLITE SAFE
# ============================================================

def add_missing_column(
    cursor,
    table_name,
    column_name,
    column_definition
):

    cursor.execute(
        "PRAGMA table_info(" + table_name + ")"
    )

    columns = cursor.fetchall()

    existing_columns = [
        column[1]
        for column in columns
    ]

    if column_name not in existing_columns:

        cursor.execute(
            "ALTER TABLE "
            + table_name
            + " ADD COLUMN "
            + column_name
            + " "
            + column_definition
        )


# ============================================================
# STUDENT FUNCTIONS
# ============================================================

def add_student(
    school_id,
    password,
    name,
    course,
    year,
    section
):

    connection = get_connection()
    cursor = connection.cursor()

    try:

        now = get_current_datetime()

        cursor.execute("""
            INSERT INTO students
            (
                school_id,
                password,
                name,
                course,
                year,
                section,
                status,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE', ?, ?)
        """, (
            school_id,
            password,
            name,
            course,
            year,
            section,
            now,
            now
        ))

        connection.commit()

        student_id = cursor.lastrowid

        connection.close()

        return student_id

    except sqlite3.IntegrityError:

        connection.close()

        return None


def get_student_by_school_id(school_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            school_id,
            password,
            name,
            course,
            year,
            section
        FROM students
        WHERE school_id = ?
    """, (school_id,))

    student = cursor.fetchone()

    connection.close()

    return student


def get_student_by_id(student_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            school_id,
            password,
            name,
            course,
            year,
            section
        FROM students
        WHERE id = ?
    """, (student_id,))

    student = cursor.fetchone()

    connection.close()

    return student


def get_all_students():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            school_id,
            name,
            course,
            year,
            section
        FROM students
        ORDER BY id DESC
    """)

    students = cursor.fetchall()

    connection.close()

    return students


# ============================================================
# TEACHER FUNCTIONS
# ============================================================

def add_teacher(
    teacher_id,
    password,
    name
):

    connection = get_connection()
    cursor = connection.cursor()

    try:

        now = get_current_datetime()

        cursor.execute("""
            INSERT INTO teachers
            (
                teacher_id,
                password,
                name,
                status,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, 'ACTIVE', ?, ?)
        """, (
            teacher_id,
            password,
            name,
            now,
            now
        ))

        connection.commit()

        teacher_database_id = cursor.lastrowid

        connection.close()

        return teacher_database_id

    except sqlite3.IntegrityError:

        connection.close()

        return None


def get_teacher_by_teacher_id(teacher_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            teacher_id,
            password,
            name
        FROM teachers
        WHERE teacher_id = ?
    """, (teacher_id,))

    teacher = cursor.fetchone()

    connection.close()

    return teacher


def get_teacher_by_id(teacher_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            teacher_id,
            password,
            name
        FROM teachers
        WHERE id = ?
    """, (teacher_id,))

    teacher = cursor.fetchone()

    connection.close()

    return teacher


def get_all_teachers():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            teacher_id,
            name
        FROM teachers
        ORDER BY id DESC
    """)

    teachers = cursor.fetchall()

    connection.close()

    return teachers


# ============================================================
# SCHEDULE FUNCTIONS
# ============================================================

def add_schedule(
    teacher_id,
    course,
    subject,
    section,
    year,
    day,
    start_time,
    end_time
):

    connection = get_connection()
    cursor = connection.cursor()

    try:

        now = get_current_datetime()

        cursor.execute("""
            INSERT INTO schedules
            (
                teacher_id,
                course,
                subject,
                section,
                year,
                day,
                start_time,
                end_time,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            teacher_id,
            course,
            subject,
            section,
            year,
            day,
            start_time,
            end_time,
            now,
            now
        ))

        connection.commit()

        schedule_id = cursor.lastrowid

        connection.close()

        return schedule_id

    except sqlite3.IntegrityError:

        connection.close()

        return None


def get_schedule_by_id(schedule_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            teacher_id,
            course,
            subject,
            section,
            year,
            day,
            start_time,
            end_time
        FROM schedules
        WHERE id = ?
    """, (schedule_id,))

    schedule = cursor.fetchone()

    connection.close()

    return schedule


def get_teacher_schedules(teacher_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            teacher_id,
            course,
            subject,
            section,
            year,
            day,
            start_time,
            end_time
        FROM schedules
        WHERE teacher_id = ?
        ORDER BY day, start_time
    """, (teacher_id,))

    schedules = cursor.fetchall()

    connection.close()

    return schedules


def get_all_schedules():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            teacher_id,
            course,
            subject,
            section,
            year,
            day,
            start_time,
            end_time
        FROM schedules
        ORDER BY day, start_time
    """)

    schedules = cursor.fetchall()

    connection.close()

    return schedules


# ============================================================
# STUDENT CLASS FUNCTIONS
# ============================================================

def add_student_class(
    student_id,
    schedule_id
):

    connection = get_connection()
    cursor = connection.cursor()

    try:

        now = get_current_datetime()

        cursor.execute("""
            INSERT INTO student_classes
            (
                student_id,
                schedule_id,
                joined_at
            )
            VALUES (?, ?, ?)
        """, (
            student_id,
            schedule_id,
            now
        ))

        connection.commit()

        class_id = cursor.lastrowid

        connection.close()

        return class_id

    except sqlite3.IntegrityError:

        connection.close()

        return None


def get_student_classes(student_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            student_classes.id,
            schedules.id,
            schedules.teacher_id,
            schedules.course,
            schedules.subject,
            schedules.section,
            schedules.year,
            schedules.day,
            schedules.start_time,
            schedules.end_time
        FROM student_classes

        INNER JOIN schedules
            ON student_classes.schedule_id = schedules.id

        WHERE student_classes.student_id = ?

        ORDER BY
            schedules.day,
            schedules.start_time
    """, (student_id,))

    classes = cursor.fetchall()

    connection.close()

    return classes


def student_is_enrolled(
    student_id,
    schedule_id
):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id
        FROM student_classes
        WHERE student_id = ?
          AND schedule_id = ?
    """, (
        student_id,
        schedule_id
    ))

    result = cursor.fetchone()

    connection.close()

    return result is not None


# ============================================================
# QR CODE FUNCTIONS
# ============================================================

def save_student_qr(
    student_id,
    schedule_id,
    token,
    qr_file,
    created_at
):

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
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
            qr_file,
            created_at
        ))

        connection.commit()

        qr_id = cursor.lastrowid

        connection.close()

        return qr_id

    except sqlite3.IntegrityError:

        connection.close()

        return None


def get_student_qr(
    student_id,
    schedule_id
):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            student_id,
            schedule_id,
            token,
            qr_file,
            created_at
        FROM qr_codes
        WHERE student_id = ?
          AND schedule_id = ?
    """, (
        student_id,
        schedule_id
    ))

    qr = cursor.fetchone()

    connection.close()

    return qr


def get_qr_by_token(token):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            student_id,
            schedule_id,
            token,
            qr_file,
            created_at
        FROM qr_codes
        WHERE token = ?
    """, (token,))

    qr = cursor.fetchone()

    connection.close()

    return qr


# ============================================================
# ATTENDANCE FUNCTIONS
# ============================================================

def add_attendance(
    student_id,
    schedule_id,
    attendance_date,
    attendance_time,
    status,
    method
):

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            INSERT INTO attendance
            (
                student_id,
                schedule_id,
                attendance_date,
                attendance_time,
                status,
                method
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            student_id,
            schedule_id,
            attendance_date,
            attendance_time,
            status,
            method
        ))

        connection.commit()

        attendance_id = cursor.lastrowid

        connection.close()

        return attendance_id

    except sqlite3.IntegrityError:

        connection.close()

        return None


def get_student_attendance(student_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            attendance.id,
            attendance.student_id,
            attendance.schedule_id,
            attendance.attendance_date,
            attendance.attendance_time,
            attendance.status,
            attendance.method,
            schedules.subject,
            schedules.course,
            schedules.section,
            schedules.year
        FROM attendance

        INNER JOIN schedules
            ON attendance.schedule_id = schedules.id

        WHERE attendance.student_id = ?

        ORDER BY
            attendance.attendance_date DESC,
            attendance.attendance_time DESC
    """, (student_id,))

    records = cursor.fetchall()

    connection.close()

    return records


def get_teacher_attendance(teacher_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            attendance.id,
            attendance.student_id,
            students.school_id,
            students.name,
            attendance.schedule_id,
            schedules.subject,
            schedules.course,
            schedules.year,
            schedules.section,
            attendance.attendance_date,
            attendance.attendance_time,
            attendance.status,
            attendance.method
        FROM attendance

        INNER JOIN students
            ON attendance.student_id = students.id

        INNER JOIN schedules
            ON attendance.schedule_id = schedules.id

        WHERE schedules.teacher_id = ?

        ORDER BY
            attendance.attendance_date DESC,
            attendance.attendance_time DESC
    """, (teacher_id,))

    records = cursor.fetchall()

    connection.close()

    return records


# ============================================================
# ATTENDANCE SESSION FUNCTIONS
# ============================================================

def create_attendance_session_record(
    schedule_id,
    teacher_id,
    session_token,
    session_date,
    created_at,
    expires_at,
    status="ACTIVE"
):

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            INSERT INTO attendance_sessions
            (
                schedule_id,
                teacher_id,
                session_token,
                session_date,
                created_at,
                expires_at,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            schedule_id,
            teacher_id,
            session_token,
            session_date,
            created_at,
            expires_at,
            status
        ))

        connection.commit()

        session_id = cursor.lastrowid

        connection.close()

        return session_id

    except sqlite3.IntegrityError:

        connection.close()

        return None


def get_attendance_session(session_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            schedule_id,
            teacher_id,
            session_token,
            session_date,
            created_at,
            expires_at,
            status
        FROM attendance_sessions
        WHERE id = ?
    """, (session_id,))

    session = cursor.fetchone()

    connection.close()

    return session


def get_attendance_session_by_token(session_token):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            schedule_id,
            teacher_id,
            session_token,
            session_date,
            created_at,
            expires_at,
            status
        FROM attendance_sessions
        WHERE session_token = ?
    """, (session_token,))

    session = cursor.fetchone()

    connection.close()

    return session


def close_attendance_session(session_id):

    connection = get_connection()

    connection.execute("""
        UPDATE attendance_sessions
        SET status = 'CLOSED'
        WHERE id = ?
    """, (session_id,))

    connection.commit()
    connection.close()


def expire_attendance_session(session_id):

    connection = get_connection()

    connection.execute("""
        UPDATE attendance_sessions
        SET status = 'EXPIRED'
        WHERE id = ?
    """, (session_id,))

    connection.commit()
    connection.close()


# ============================================================
# FACE DATA FUNCTIONS
# ============================================================

def save_face_data(
    student_id,
    encoding_file,
    registered_at=None
):

    connection = get_connection()
    cursor = connection.cursor()

    if registered_at is None:
        registered_at = get_current_datetime()

    try:

        cursor.execute("""
            INSERT INTO face_data
            (
                student_id,
                encoding_file,
                registered_at
            )
            VALUES (?, ?, ?)
        """, (
            student_id,
            encoding_file,
            registered_at
        ))

        connection.commit()

        face_id = cursor.lastrowid

        connection.close()

        return face_id

    except sqlite3.IntegrityError:

        connection.close()

        return None


def get_face_data(student_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            student_id,
            encoding_file,
            registered_at
        FROM face_data
        WHERE student_id = ?
        ORDER BY id DESC
    """, (student_id,))

    records = cursor.fetchall()

    connection.close()

    return records


def get_all_face_data():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            student_id,
            encoding_file,
            registered_at
        FROM face_data
        ORDER BY id DESC
    """)

    records = cursor.fetchall()

    connection.close()

    return records


# ============================================================
# FINGERPRINT FUNCTIONS
# ============================================================

def save_fingerprint(
    student_id,
    fingerprint_id,
    finger_name=None,
    created_at=None
):

    connection = get_connection()
    cursor = connection.cursor()

    if created_at is None:
        created_at = get_current_datetime()

    try:

        cursor.execute("""
            INSERT INTO fingerprints
            (
                student_id,
                fingerprint_id,
                finger_name,
                created_at
            )
            VALUES (?, ?, ?, ?)
        """, (
            student_id,
            fingerprint_id,
            finger_name,
            created_at
        ))

        connection.commit()

        fingerprint_database_id = cursor.lastrowid

        connection.close()

        return fingerprint_database_id

    except sqlite3.IntegrityError:

        connection.close()

        return None


def get_student_fingerprints(student_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            student_id,
            fingerprint_id,
            finger_name,
            created_at
        FROM fingerprints
        WHERE student_id = ?
        ORDER BY id DESC
    """, (student_id,))

    records = cursor.fetchall()

    connection.close()

    return records


def get_fingerprint_by_id(fingerprint_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            student_id,
            fingerprint_id,
            finger_name,
            created_at
        FROM fingerprints
        WHERE fingerprint_id = ?
    """, (fingerprint_id,))

    record = cursor.fetchone()

    connection.close()

    return record


# ============================================================
# LOGIN HISTORY
# ============================================================

def record_student_login(student_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            school_id,
            name,
            course,
            year,
            section
        FROM students
        WHERE id = ?
    """, (student_id,))

    student = cursor.fetchone()

    if student is None:
        connection.close()
        return False

    now = datetime.now()

    login_date = now.strftime("%Y-%m-%d")
    login_time = now.strftime("%H:%M:%S")

    cursor.execute("""
        INSERT INTO login_history
        (
            role,
            account_id,
            account_number,
            name,
            course,
            year,
            section,
            login_date,
            login_time
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "Student",
        student[0],
        student[1],
        student[2],
        student[3],
        student[4],
        student[5],
        login_date,
        login_time
    ))

    connection.commit()
    connection.close()

    return True


def record_teacher_login(teacher_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            teacher_id,
            name
        FROM teachers
        WHERE id = ?
    """, (teacher_id,))

    teacher = cursor.fetchone()

    if teacher is None:
        connection.close()
        return False

    now = datetime.now()

    login_date = now.strftime("%Y-%m-%d")
    login_time = now.strftime("%H:%M:%S")

    cursor.execute("""
        INSERT INTO login_history
        (
            role,
            account_id,
            account_number,
            name,
            course,
            year,
            section,
            login_date,
            login_time
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "Teacher",
        teacher[0],
        teacher[1],
        teacher[2],
        None,
        None,
        None,
        login_date,
        login_time
    ))

    connection.commit()
    connection.close()

    return True


def get_login_history():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            role,
            account_id,
            account_number,
            name,
            course,
            year,
            section,
            login_date,
            login_time
        FROM login_history
        ORDER BY id DESC
    """)

    records = cursor.fetchall()

    connection.close()

    return records


def get_student_login_history(student_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            role,
            account_id,
            account_number,
            name,
            course,
            year,
            section,
            login_date,
            login_time
        FROM login_history
        WHERE role = 'Student'
          AND account_id = ?
        ORDER BY id DESC
    """, (student_id,))

    records = cursor.fetchall()

    connection.close()

    return records


def get_teacher_login_history(teacher_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            role,
            account_id,
            account_number,
            name,
            course,
            year,
            section,
            login_date,
            login_time
        FROM login_history
        WHERE role = 'Teacher'
          AND account_id = ?
        ORDER BY id DESC
    """, (teacher_id,))

    records = cursor.fetchall()

    connection.close()

    return records


# ============================================================
# AUDIT LOG FUNCTIONS
# ============================================================

def add_audit_log(
    user_role,
    account_id,
    action,
    details=None
):

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            INSERT INTO audit_logs
            (
                user_role,
                account_id,
                action,
                details,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            user_role,
            account_id,
            action,
            details,
            get_current_datetime()
        ))

        connection.commit()

        audit_id = cursor.lastrowid

        connection.close()

        return audit_id

    except sqlite3.IntegrityError:

        connection.close()

        return None


def get_audit_logs():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            user_role,
            account_id,
            action,
            details,
            created_at
        FROM audit_logs
        ORDER BY id DESC
    """)

    records = cursor.fetchall()

    connection.close()

    return records


# ============================================================
# DATABASE INFORMATION
# ============================================================

def get_database_file():
    return DB_FILE


def get_database_tables():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        ORDER BY name
    """)

    tables = cursor.fetchall()

    connection.close()

    return tables


# ============================================================
# INITIALIZE DATABASE
# ============================================================

create_database()