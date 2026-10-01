import os
import sqlite3
import py_compile
import importlib.util

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE_DIR, "attendance.db")

print("=" * 70)
print("ATTENDX BIOMETRIC + QR FULL SYSTEM AUDIT")
print("=" * 70)

# ------------------------------------------------------------
# FILE CHECK
# ------------------------------------------------------------

files = [
    "main.py",
    "database.py",
    "face_system.py",
    "face_registration.py",
    "teacher_face_registration.py",
    "fingerprint_system.py"
]

print("\n[1] REQUIRED FILES")

for file in files:
    path = os.path.join(BASE_DIR, file)

    if os.path.exists(path):
        print("[OK] " + file)
    else:
        print("[MISSING] " + file)

# ------------------------------------------------------------
# PYTHON COMPILE CHECK
# ------------------------------------------------------------

print("\n[2] PYTHON SYNTAX")

for file in files:
    path = os.path.join(BASE_DIR, file)

    if os.path.exists(path):
        try:
            py_compile.compile(
                path,
                doraise=True
            )
            print("[OK] " + file)
        except Exception as error:
            print("[ERROR] " + file)
            print("       " + str(error))

# ------------------------------------------------------------
# MODULE IMPORT CHECK
# ------------------------------------------------------------

print("\n[3] MODULE IMPORTS")

modules = [
    "database",
    "face_system",
    "face_registration",
    "teacher_face_registration",
    "fingerprint_system"
]

for module in modules:
    try:
        importlib.import_module(module)
        print("[OK] " + module)
    except Exception as error:
        print("[ERROR] " + module)
        print("       " + str(error))

# ------------------------------------------------------------
# DATABASE CHECK
# ------------------------------------------------------------

print("\n[4] DATABASE")

if not os.path.exists(DB):
    print("[ERROR] attendance.db does not exist")
else:

    print("[OK] attendance.db exists")

    try:
        connection = sqlite3.connect(DB)
        cursor = connection.cursor()

        cursor.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            ORDER BY name
        """)

        tables = [
            row[0]
            for row in cursor.fetchall()
        ]

        required_tables = [
            "students",
            "teachers",
            "schedules",
            "student_classes",
            "qr_codes",
            "attendance",
            "attendance_sessions",
            "face_data",
            "fingerprints",
            "login_history"
        ]

        print("\nRequired tables:")

        for table in required_tables:

            if table in tables:
                print("[OK] " + table)
            else:
                print("[MISSING] " + table)

        print("\nAll database tables:")

        for table in tables:
            print(" - " + table)

        # ----------------------------------------------------
        # RECORD COUNTS
        # ----------------------------------------------------

        print("\nRecord counts:")

        for table in required_tables:

            if table in tables:

                try:
                    cursor.execute(
                        "SELECT COUNT(*) FROM " + table
                    )

                    count = cursor.fetchone()[0]

                    print(
                        " - "
                        + table
                        + ": "
                        + str(count)
                    )

                except Exception as error:

                    print(
                        " - "
                        + table
                        + ": ERROR "
                        + str(error)
                    )

        # ----------------------------------------------------
        # FACE REGISTRATIONS
        # ----------------------------------------------------

        if "face_data" in tables:

            print("\nFACE REGISTRATIONS:")

            cursor.execute("""
                SELECT
                    student_id,
                    encoding_file,
                    registered_at
                FROM face_data
            """)

            rows = cursor.fetchall()

            if not rows:
                print("[WARNING] No student face registrations found.")

            for row in rows:
                print(
                    "[FACE]",
                    row
                )

        # ----------------------------------------------------
        # FINGERPRINT REGISTRATIONS
        # ----------------------------------------------------

        if "fingerprints" in tables:

            print("\nFINGERPRINT RECORDS:")

            cursor.execute("""
                SELECT *
                FROM fingerprints
            """)

            rows = cursor.fetchall()

            if not rows:
                print("[INFO] No fingerprint records found.")

            for row in rows:
                print(
                    "[FINGERPRINT]",
                    row
                )

        # ----------------------------------------------------
        # QR RECORDS
        # ----------------------------------------------------

        if "qr_codes" in tables:

            print("\nQR RECORDS:")

            cursor.execute("""
                SELECT *
                FROM qr_codes
            """)

            rows = cursor.fetchall()

            if not rows:
                print("[WARNING] No QR records found.")

            for row in rows[:20]:
                print(
                    "[QR]",
                    row
                )

            if len(rows) > 20:
                print(
                    "... and",
                    len(rows) - 20,
                    "more QR records"
                )

        connection.close()

    except Exception as error:

        print("[DATABASE ERROR]")
        print(error)

# ------------------------------------------------------------
# QR FOLDER
# ------------------------------------------------------------

print("\n[5] QR FILES")

qr_folder = os.path.join(
    BASE_DIR,
    "qr_codes"
)

if os.path.isdir(qr_folder):

    qr_files = [
        x for x in os.listdir(qr_folder)
        if os.path.isfile(
            os.path.join(qr_folder, x)
        )
    ]

    print(
        "[OK] qr_codes folder:",
        len(qr_files),
        "files"
    )

else:

    print("[WARNING] qr_codes folder not found.")

# ------------------------------------------------------------
# FACE FOLDER
# ------------------------------------------------------------

print("\n[6] FACE FILES")

face_folder = os.path.join(
    BASE_DIR,
    "face_data"
)

if os.path.isdir(face_folder):

    face_files = [
        x for x in os.listdir(face_folder)
        if os.path.isfile(
            os.path.join(face_folder, x)
        )
    ]

    print(
        "[OK] face_data folder:",
        len(face_files),
        "files"
    )

    for file in face_files:
        print(" - " + file)

else:

    print("[WARNING] face_data folder not found.")

# ------------------------------------------------------------
# MAIN ATTENDANCE METHODS
# ------------------------------------------------------------

print("\n[7] MAIN ATTENDANCE FLOW")

main_path = os.path.join(
    BASE_DIR,
    "main.py"
)

if os.path.exists(main_path):

    with open(
        main_path,
        "r",
        encoding="utf-8"
    ) as file:

        main = file.read()

    checks = {
        "SCAN QR": "SCAN QR" in main,
        "FACE": 'elif method == "FACE":' in main,
        "FINGERPRINT": "fingerprint_attendance_action" in main,
        "face_attendance_action": "def face_attendance_action(" in main,
        "record_attendance": "def record_attendance(" in main,
        "FACE record method": '"FACE"' in main,
        "QR record method": '"QR"' in main,
        "Fingerprint record method": '"FINGERPRINT"' in main
    }

    for name, result in checks.items():

        if result:
            print("[OK] " + name)
        else:
            print("[MISSING] " + name)

# ------------------------------------------------------------
# FACE COMPARISON
# ------------------------------------------------------------

print("\n[8] FACE MATCHING")

face_path = os.path.join(
    BASE_DIR,
    "face_system.py"
)

if os.path.exists(face_path):

    with open(
        face_path,
        "r",
        encoding="utf-8"
    ) as file:

        face = file.read()

    checks = {
        "find_student_by_face": "def find_student_by_face(" in face,
        "compare_face_encodings": "def compare_face_encodings(" in face,
        "threshold 65": "threshold=65.0" in face,
        "load_face_template": "def load_face_template(" in face,
        "validate_face_attendance": "def validate_face_attendance(" in face
    }

    for name, result in checks.items():

        if result:
            print("[OK] " + name)
        else:
            print("[MISSING] " + name)

# ------------------------------------------------------------
# FINISH
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("AUDIT COMPLETE")
print("=" * 70)

