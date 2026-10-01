import sqlite3

c = sqlite3.connect("attendance.db")

print("=" * 60)
print("ATTENDX DATABASE VERIFICATION")
print("=" * 60)

print()
print("TABLES:")

tables = c.execute("""
    SELECT name
    FROM sqlite_master
    WHERE type = 'table'
    ORDER BY name
""").fetchall()

for table in tables:
    print(" -", table[0])

print()
print("COUNTS:")

table_names = [
    "students",
    "teachers",
    "schedules",
    "student_classes",
    "qr_codes",
    "face_data",
    "fingerprints",
    "attendance",
    "attendance_sessions",
    "login_history",
    "audit_logs"
]

for table in table_names:

    exists = c.execute("""
        SELECT COUNT(*)
        FROM sqlite_master
        WHERE type = 'table'
        AND name = ?
    """, (table,)).fetchone()[0]

    if exists:
        count = c.execute(
            "SELECT COUNT(*) FROM " + table
        ).fetchone()[0]

        print(
            " -",
            table,
            ":",
            count
        )

print()
print("DATABASE:")
print("attendance.db")

c.close()

print()
print("=" * 60)
print("VERIFICATION COMPLETE")
print("=" * 60)
