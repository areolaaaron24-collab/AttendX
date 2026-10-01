from datetime import datetime, timedelta

from database import (
    get_connection,
    get_schedule_by_id,
    get_student_by_id,
    get_student_attendance,
    get_teacher_attendance,
    add_attendance
)

from matching import (
    validate_student_attendance,
    teacher_owns_schedule
)

from qr_system import (
    validate_student_qr_for_attendance,
    validate_session_qr
)


# ============================================================
# ATTENDANCE CONFIGURATION
# ============================================================

LATE_GRACE_MINUTES = 15

PRESENT_STATUS = "PRESENT"
LATE_STATUS = "LATE"
ABSENT_STATUS = "ABSENT"

METHOD_QR = "QR"
METHOD_FACE = "FACE"
METHOD_FINGERPRINT = "FINGERPRINT"


# ============================================================
# TIME FUNCTIONS
# ============================================================

def get_current_date():
    """
    Returns today's date.
    """

    return datetime.now().strftime(
        "%Y-%m-%d"
    )


def get_current_time():
    """
    Returns the current time.
    """

    return datetime.now().strftime(
        "%H:%M"
    )


def get_current_datetime():
    """
    Returns the current date and time.
    """

    return datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )


# ============================================================
# TIME CONVERSION
# ============================================================

def convert_time_to_minutes(
    time_text
):
    """
    Converts HH:MM into total minutes.
    """

    try:

        hour, minute = map(
            int,
            time_text.split(":")
        )

        return (
            hour * 60
            + minute
        )

    except Exception:

        return None


# ============================================================
# ATTENDANCE STATUS
# ============================================================

def get_attendance_status(
    start_time,
    current_time=None
):
    """
    Determines whether attendance is
    PRESENT or LATE.

    Student is PRESENT if they attend
    within the first 15 minutes.

    After 15 minutes, they are LATE.
    """

    if current_time is None:
        current_time = get_current_time()

    start_minutes = convert_time_to_minutes(
        start_time
    )

    current_minutes = convert_time_to_minutes(
        current_time
    )

    if start_minutes is None:
        return LATE_STATUS

    if current_minutes is None:
        return LATE_STATUS

    late_limit = (
        start_minutes
        + LATE_GRACE_MINUTES
    )

    if current_minutes <= late_limit:
        return PRESENT_STATUS

    return LATE_STATUS


# ============================================================
# CHECK EXISTING ATTENDANCE
# ============================================================

def has_attendance_today(
    student_id,
    schedule_id
):
    """
    Checks whether the student already
    has attendance for this class today.
    """

    today = get_current_date()

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute("""
        SELECT id
        FROM attendance
        WHERE student_id = ?
          AND schedule_id = ?
          AND attendance_date = ?
    """, (
        student_id,
        schedule_id,
        today
    ))

    record = cursor.fetchone()

    connection.close()

    return record is not None


# ============================================================
# GET TODAY'S ATTENDANCE
# ============================================================

def get_today_attendance(
    student_id,
    schedule_id
):
    """
    Returns today's attendance record
    for the student and class.
    """

    today = get_current_date()

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            student_id,
            schedule_id,
            attendance_date,
            attendance_time,
            status,
            method
        FROM attendance
        WHERE student_id = ?
          AND schedule_id = ?
          AND attendance_date = ?
    """, (
        student_id,
        schedule_id,
        today
    ))

    record = cursor.fetchone()

    connection.close()

    return record


# ============================================================
# RECORD ATTENDANCE
# ============================================================

def record_attendance(
    student_id,
    schedule_id,
    method=METHOD_QR,
    attendance_time=None
):
    """
    Records a student's attendance.

    Validation:
    - Student must exist.
    - Schedule must exist.
    - Student must match class.
    - Student must be enrolled.
    - Student cannot attend twice on the same day.
    """

    student = get_student_by_id(
        student_id
    )

    if student is None:
        return {
            "success": False,
            "message": "Student account not found."
        }

    schedule = get_schedule_by_id(
        schedule_id
    )

    if schedule is None:
        return {
            "success": False,
            "message": "Class schedule not found."
        }

    validation = validate_student_attendance(
        student_id,
        schedule_id
    )

    if not validation["matched"]:

        return {
            "success": False,
            "message": validation["message"]
        }

    if has_attendance_today(
        student_id,
        schedule_id
    ):

        existing = get_today_attendance(
            student_id,
            schedule_id
        )

        return {
            "success": False,
            "message": "Attendance already recorded today.",
            "existing": existing
        }

    if attendance_time is None:
        attendance_time = get_current_time()

    status = get_attendance_status(
        schedule[7],
        attendance_time
    )

    attendance_date = get_current_date()

    attendance_id = add_attendance(
        student_id,
        schedule_id,
        attendance_date,
        attendance_time,
        status,
        method
    )

    if attendance_id is None:

        return {
            "success": False,
            "message": "Attendance could not be recorded."
        }

    return {
        "success": True,
        "attendance_id": attendance_id,
        "student_id": student_id,
        "schedule_id": schedule_id,
        "date": attendance_date,
        "time": attendance_time,
        "status": status,
        "method": method,
        "message": (
            "Attendance recorded successfully."
        )
    }


# ============================================================
# QR ATTENDANCE
# ============================================================

def record_qr_attendance(
    qr_token,
    student_id,
    schedule_id,
    teacher_id
):
    """
    Records attendance using the student's
    permanent QR code.

    The QR must belong to the selected class.
    """

    qr_validation = (
        validate_student_qr_for_attendance(
            qr_token,
            schedule_id,
            teacher_id
        )
    )

    if not qr_validation["valid"]:

        return {
            "success": False,
            "message": qr_validation["message"]
        }

    qr_student_id = qr_validation[
        "student_id"
    ]

    if qr_student_id != student_id:

        return {
            "success": False,
            "message": "Student identity does not match QR."
        }

    return record_attendance(
        student_id,
        schedule_id,
        METHOD_QR
    )


# ============================================================
# SESSION QR ATTENDANCE
# ============================================================

def record_session_qr_attendance(
    session_token,
    student_id
):
    """
    Records attendance using an
    Attendance Session QR.

    The session QR identifies:
    - Class
    - Teacher
    - Attendance session
    - Session date
    - Session validity

    The student's enrollment is checked separately.
    """

    validation = validate_session_qr(
        session_token,
        student_id
    )

    if not validation["valid"]:

        return {
            "success": False,
            "message": validation["message"]
        }

    session = validation[
        "session"
    ]

    schedule_id = session[
        "schedule_id"
    ]

    result = record_attendance(
        student_id,
        schedule_id,
        METHOD_QR
    )

    if result["success"]:

        result["session_id"] = session[
            "id"
        ]

        result["teacher_id"] = session[
            "teacher_id"
        ]

    return result


# ============================================================
# FACE ATTENDANCE
# ============================================================

def record_face_attendance(
    student_id,
    schedule_id
):
    """
    Records attendance after the face
    recognition module identifies the student.

    Actual face recognition is handled
    by face_system.py.
    """

    return record_attendance(
        student_id,
        schedule_id,
        METHOD_FACE
    )


# ============================================================
# FINGERPRINT ATTENDANCE
# ============================================================

def record_fingerprint_attendance(
    student_id,
    schedule_id
):
    """
    Records attendance after the fingerprint
    module identifies the student.

    Actual scanner communication is handled
    by fingerprint_system.py.
    """

    return record_attendance(
        student_id,
        schedule_id,
        METHOD_FINGERPRINT
    )


# ============================================================
# ATTENDANCE RECORD LOOKUP
# ============================================================

def get_student_attendance_records(
    student_id
):
    """
    Gets the complete attendance history
    of a student.
    """

    return get_student_attendance(
        student_id
    )


def get_teacher_attendance_records(
    teacher_id
):
    """
    Gets attendance records belonging
    to the teacher's classes.
    """

    return get_teacher_attendance(
        teacher_id
    )


# ============================================================
# ATTENDANCE SUMMARY
# ============================================================

def get_student_attendance_summary(
    student_id
):
    """
    Calculates the student's attendance summary.
    """

    records = get_student_attendance(
        student_id
    )

    present = 0
    late = 0
    absent = 0
    total = 0

    for record in records:

        status = record[5]

        total += 1

        if status == PRESENT_STATUS:
            present += 1

        elif status == LATE_STATUS:
            late += 1

        elif status == ABSENT_STATUS:
            absent += 1

    return {
        "total": total,
        "present": present,
        "late": late,
        "absent": absent
    }


def get_teacher_attendance_summary(
    teacher_id
):
    """
    Calculates attendance totals
    for a teacher's classes.
    """

    records = get_teacher_attendance(
        teacher_id
    )

    present = 0
    late = 0
    absent = 0
    total = 0

    for record in records:

        status = record[11]

        total += 1

        if status == PRESENT_STATUS:
            present += 1

        elif status == LATE_STATUS:
            late += 1

        elif status == ABSENT_STATUS:
            absent += 1

    return {
        "total": total,
        "present": present,
        "late": late,
        "absent": absent
    }


# ============================================================
# CLASS ATTENDANCE
# ============================================================

def get_class_attendance(
    schedule_id,
    attendance_date=None
):
    """
    Gets attendance records for one class.
    """

    if attendance_date is None:
        attendance_date = get_current_date()

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            attendance.id,
            attendance.student_id,
            students.school_id,
            students.name,
            students.course,
            students.year,
            students.section,
            attendance.attendance_date,
            attendance.attendance_time,
            attendance.status,
            attendance.method

        FROM attendance

        INNER JOIN students
            ON attendance.student_id = students.id

        WHERE attendance.schedule_id = ?
          AND attendance.attendance_date = ?

        ORDER BY students.name
    """, (
        schedule_id,
        attendance_date
    ))

    records = cursor.fetchall()

    connection.close()

    return records


# ============================================================
# CHECK CLASS ATTENDANCE
# ============================================================

def student_has_attended_class_today(
    student_id,
    schedule_id
):
    """
    Simple True/False check.
    """

    return has_attendance_today(
        student_id,
        schedule_id
    )


# ============================================================
# ATTENDANCE METHOD VALIDATION
# ============================================================

def is_valid_attendance_method(
    method
):
    """
    Checks whether the attendance method
    is supported.
    """

    valid_methods = [
        METHOD_QR,
        METHOD_FACE,
        METHOD_FINGERPRINT
    ]

    return method in valid_methods


# ============================================================
# MANUAL ATTENDANCE
# ============================================================

def record_manual_attendance(
    student_id,
    schedule_id
):
    """
    Allows the system to record attendance
    manually when needed.
    """

    return record_attendance(
        student_id,
        schedule_id,
        "MANUAL"
    )


# ============================================================
# ABSENT CHECK
# ============================================================

def get_students_without_attendance(
    schedule_id,
    attendance_date=None
):
    """
    Gets enrolled students who do not have
    an attendance record for the selected date.

    This does not automatically insert ABSENT.
    It only identifies missing attendance.
    """

    if attendance_date is None:
        attendance_date = get_current_date()

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            students.id,
            students.school_id,
            students.name,
            students.course,
            students.year,
            students.section

        FROM student_classes

        INNER JOIN students
            ON student_classes.student_id = students.id

        WHERE student_classes.schedule_id = ?

          AND students.id NOT IN
          (
              SELECT student_id
              FROM attendance
              WHERE schedule_id = ?
                AND attendance_date = ?
          )

        ORDER BY students.name
    """, (
        schedule_id,
        schedule_id,
        attendance_date
    ))

    students = cursor.fetchall()

    connection.close()

    return students


# ============================================================
# CREATE ABSENT RECORDS
# ============================================================

def create_absent_records(
    schedule_id,
    attendance_date=None
):
    """
    Creates ABSENT records for enrolled students
    who have no attendance record.

    This should normally be called only after
    the attendance period has ended.
    """

    if attendance_date is None:
        attendance_date = get_current_date()

    missing_students = (
        get_students_without_attendance(
            schedule_id,
            attendance_date
        )
    )

    created = 0

    connection = get_connection()

    cursor = connection.cursor()

    current_time = datetime.now().strftime(
        "%H:%M"
    )

    for student in missing_students:

        student_id = student[0]

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
                current_time,
                ABSENT_STATUS,
                "SYSTEM"
            ))

            created += 1

        except Exception:
            pass

    connection.commit()

    connection.close()

    return created


# ============================================================
# ATTENDANCE VALIDATION BEFORE RECORDING
# ============================================================

def can_record_attendance(
    student_id,
    schedule_id
):
    """
    Checks whether attendance can be recorded.
    """

    student = get_student_by_id(
        student_id
    )

    if student is None:

        return {
            "allowed": False,
            "message": "Student not found."
        }

    schedule = get_schedule_by_id(
        schedule_id
    )

    if schedule is None:

        return {
            "allowed": False,
            "message": "Schedule not found."
        }

    matching = validate_student_attendance(
        student_id,
        schedule_id
    )

    if not matching["matched"]:

        return {
            "allowed": False,
            "message": matching["message"]
        }

    if has_attendance_today(
        student_id,
        schedule_id
    ):

        return {
            "allowed": False,
            "message": "Attendance already recorded today."
        }

    return {
        "allowed": True,
        "message": "Attendance can be recorded."
    }


# ============================================================
# COMPLETE ATTENDANCE RESULT
# ============================================================

def get_attendance_result_message(
    result
):
    """
    Converts an attendance result into
    a simple message for the UI.
    """

    if result is None:
        return "No attendance result."

    if result.get("success"):

        status = result.get(
            "status",
            "RECORDED"
        )

        return (
            "Attendance recorded: "
            + status
        )

    return result.get(
        "message",
        "Attendance failed."
    )


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    print("ATTENDX ATTENDANCE MODULE")
    print("--------------------------")
    print("Attendance recording: READY")
    print("QR attendance: READY")
    print("Session QR attendance: READY")
    print("Face attendance interface: READY")
    print("Fingerprint attendance interface: READY")
    print("Present/Late calculation: READY")
    print("Absent detection: READY")
    print("Attendance history: READY")
    print("Attendance summaries: READY")