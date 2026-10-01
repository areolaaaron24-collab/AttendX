import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "attendance.db")


def show_table(cursor, table_name):

    print("\n")
    print("=" * 90)
    print("TABLE:", table_name)
    print("=" * 90)

    cursor.execute("SELECT * FROM " + table_name)

    rows = cursor.fetchall()

    if not rows:
        print("No records found.")
        return

    columns = [description[0] for description in cursor.description]

    print(" | ".join(columns))
    print("-" * 90)

    for row in rows:
        print(" | ".join(str(value) for value in row))


connection = sqlite3.connect(DB_FILE)

cursor = connection.cursor()

print("=" * 90)
print("                 ATTENDX DATABASE VIEWER")
print("=" * 90)

tables = [
    "students",
    "teachers",
    "schedules",
    "student_classes",
    "qr_codes",
    "attendance",
    "attendance_sessions",
    "login_history"
]

for table in tables:

    try:
        show_table(cursor, table)

    except sqlite3.OperationalError:
        print("\n")
        print("=" * 90)
        print("TABLE:", table)
        print("=" * 90)
        print("Table does not exist yet.")

connection.close()

print("\n")
print("=" * 90)
print("DATABASE VIEWING FINISHED")
print("=" * 90)

