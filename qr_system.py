import os
import secrets
from datetime import datetime

import qrcode
from PIL import Image

from database import (
    get_connection,
    get_student_qr,
    get_qr_by_token,
    save_student_qr,
    get_attendance_session,
    get_attendance_session_by_token,
    create_attendance_session_record,
    close_attendance_session,
    expire_attendance_session
)

from matching import (
    validate_student_attendance,
    validate_qr_attendance,
    teacher_owns_schedule
)


# ============================================================
# QR SYSTEM CONFIGURATION
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

QR_FOLDER = os.path.join(
    BASE_DIR,
    "qr_codes"
)

STUDENT_QR_PREFIX = "ATTENDX-STUDENT-"
SESSION_QR_PREFIX = "ATTENDX-SESSION-"


# ============================================================
# FOLDER SETUP
# ============================================================

def create_qr_folder():
    """
    Creates the QR code folder if it does not exist.
    """

    os.makedirs(
        QR_FOLDER,
        exist_ok=True
    )


# ============================================================
# GENERATE STUDENT QR TOKEN
# ============================================================

def generate_student_token():
    """
    Creates a unique random token for a student class QR.

    The QR contains only the token.
    No password or biometric information is stored.
    """

    return (
        STUDENT_QR_PREFIX
        + secrets.token_hex(20)
    )


# ============================================================
# GENERATE ATTENDANCE SESSION TOKEN
# ============================================================

def generate_session_token():
    """
    Creates a unique random token for an
    attendance session.
    """

    return (
        SESSION_QR_PREFIX
        + secrets.token_hex(20)
    )


# ============================================================
# GENERATE QR IMAGE
# ============================================================

def generate_qr_image(
    token,
    filename
):
    """
    Generates a PNG QR code containing the token.
    """

    create_qr_folder()

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=12,
        border=5
    )

    qr.add_data(token)

    qr.make(
        fit=True
    )

    image = qr.make_image(
        fill_color="black",
        back_color="white"
    )

    image.save(
        filename
    )

    return filename


# ============================================================
# CREATE STUDENT CLASS QR
# ============================================================

def create_student_class_qr(
    student_id,
    schedule_id
):
    """
    Creates one permanent QR for a student's
    specific enrolled class.

    One student + one class = one unique QR.
    """

    create_qr_folder()

    existing_qr = get_student_qr(
        student_id,
        schedule_id
    )

    if existing_qr is not None:

        qr_file = existing_qr[4]

        if qr_file and os.path.exists(qr_file):
            return {
                "success": True,
                "qr_id": existing_qr[0],
                "student_id": existing_qr[1],
                "schedule_id": existing_qr[2],
                "token": existing_qr[3],
                "qr_file": existing_qr[4],
                "created_at": existing_qr[5],
                "existing": True
            }

    token = generate_student_token()

    filename = os.path.join(
        QR_FOLDER,
        "student_"
        + str(student_id)
        + "_class_"
        + str(schedule_id)
        + ".png"
    )

    generate_qr_image(
        token,
        filename
    )

    created_at = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    qr_id = save_student_qr(
        student_id,
        schedule_id,
        token,
        filename,
        created_at
    )

    if qr_id is None:

        existing_qr = get_student_qr(
            student_id,
            schedule_id
        )

        if existing_qr is None:
            return {
                "success": False,
                "message": "Unable to create student QR."
            }

        return {
            "success": True,
            "qr_id": existing_qr[0],
            "student_id": existing_qr[1],
            "schedule_id": existing_qr[2],
            "token": existing_qr[3],
            "qr_file": existing_qr[4],
            "created_at": existing_qr[5],
            "existing": True
        }

    return {
        "success": True,
        "qr_id": qr_id,
        "student_id": student_id,
        "schedule_id": schedule_id,
        "token": token,
        "qr_file": filename,
        "created_at": created_at,
        "existing": False
    }


# ============================================================
# GET STUDENT CLASS QR
# ============================================================

def get_student_class_qr(
    student_id,
    schedule_id
):
    """
    Gets an existing student class QR.
    """

    qr = get_student_qr(
        student_id,
        schedule_id
    )

    if qr is None:
        return None

    return {
        "id": qr[0],
        "student_id": qr[1],
        "schedule_id": qr[2],
        "token": qr[3],
        "qr_file": qr[4],
        "created_at": qr[5]
    }


# ============================================================
# GET QR INFORMATION
# ============================================================

def get_student_qr_information(
    token
):
    """
    Finds a student QR using its token.
    """

    qr = get_qr_by_token(
        token
    )

    if qr is None:
        return None

    return {
        "id": qr[0],
        "student_id": qr[1],
        "schedule_id": qr[2],
        "token": qr[3],
        "qr_file": qr[4],
        "created_at": qr[5]
    }


# ============================================================
# VALIDATE STUDENT QR
# ============================================================

def validate_student_qr(
    token
):
    """
    Checks whether a student QR exists.
    """

    qr_information = get_student_qr_information(
        token
    )

    if qr_information is None:
        return {
            "valid": False,
            "message": "Invalid student QR code."
        }

    return {
        "valid": True,
        "message": "Student QR code is valid.",
        "qr": qr_information
    }


# ============================================================
# VALIDATE STUDENT QR FOR ATTENDANCE
# ============================================================

def validate_student_qr_for_attendance(
    token,
    schedule_id,
    teacher_id
):
    """
    Validates a student's permanent QR
    against the currently selected class
    and teacher.

    This prevents a QR from another class
    from being accepted.
    """

    qr_information = get_student_qr_information(
        token
    )

    if qr_information is None:
        return {
            "valid": False,
            "message": "Invalid QR code."
        }

    qr_student_id = qr_information[
        "student_id"
    ]

    qr_schedule_id = qr_information[
        "schedule_id"
    ]

    if qr_schedule_id != schedule_id:
        return {
            "valid": False,
            "message": "This QR code belongs to another class."
        }

    if not teacher_owns_schedule(
        teacher_id,
        schedule_id
    ):
        return {
            "valid": False,
            "message": "Teacher does not own this class."
        }

    matching = validate_qr_attendance(
        qr_student_id,
        schedule_id,
        teacher_id
    )

    if not matching["matched"]:
        return {
            "valid": False,
            "message": matching["message"]
        }

    return {
        "valid": True,
        "message": "Student QR successfully verified.",
        "student_id": qr_student_id,
        "schedule_id": schedule_id,
        "qr": qr_information
    }


# ============================================================
# CREATE ATTENDANCE SESSION
# ============================================================

def create_attendance_session(
    teacher_id,
    schedule_id,
    duration_minutes=5
):
    """
    Creates a temporary attendance session.

    The session QR is valid only for the
    configured duration.
    """

    from datetime import timedelta

    create_qr_folder()

    connection = get_connection()

    cursor = connection.cursor()

    # --------------------------------------------------------
    # CLOSE PREVIOUS ACTIVE SESSION
    # --------------------------------------------------------

    today = datetime.now().strftime(
        "%Y-%m-%d"
    )

    cursor.execute("""
        UPDATE attendance_sessions
        SET status = 'CLOSED'
        WHERE teacher_id = ?
          AND schedule_id = ?
          AND session_date = ?
          AND status = 'ACTIVE'
    """, (
        teacher_id,
        schedule_id,
        today
    ))

    connection.commit()

    connection.close()

    # --------------------------------------------------------
    # CREATE NEW SESSION
    # --------------------------------------------------------

    now = datetime.now()

    created_at = now.strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    expires = (
        now
        + timedelta(
            minutes=duration_minutes
        )
    )

    expires_at = expires.strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    session_token = generate_session_token()

    session_date = now.strftime(
        "%Y-%m-%d"
    )

    session_id = create_attendance_session_record(
        schedule_id,
        teacher_id,
        session_token,
        session_date,
        created_at,
        expires_at,
        "ACTIVE"
    )

    filename = os.path.join(
        QR_FOLDER,
        "attendance_session_"
        + str(session_id)
        + ".png"
    )

    generate_qr_image(
        session_token,
        filename
    )

    return {
        "success": True,
        "session_id": session_id,
        "schedule_id": schedule_id,
        "teacher_id": teacher_id,
        "session_token": session_token,
        "session_date": session_date,
        "created_at": created_at,
        "expires_at": expires_at,
        "status": "ACTIVE",
        "qr_file": filename
    }


# ============================================================
# GET ATTENDANCE SESSION
# ============================================================

def get_session(
    session_id
):
    """
    Gets attendance session information.
    """

    session = get_attendance_session(
        session_id
    )

    if session is None:
        return None

    return {
        "id": session[0],
        "schedule_id": session[1],
        "teacher_id": session[2],
        "session_token": session[3],
        "session_date": session[4],
        "created_at": session[5],
        "expires_at": session[6],
        "status": session[7]
    }


# ============================================================
# GET SESSION USING TOKEN
# ============================================================

def get_session_by_token(
    token
):
    """
    Finds an attendance session using
    the QR token.
    """

    session = get_attendance_session_by_token(
        token
    )

    if session is None:
        return None

    return {
        "id": session[0],
        "schedule_id": session[1],
        "teacher_id": session[2],
        "session_token": session[3],
        "session_date": session[4],
        "created_at": session[5],
        "expires_at": session[6],
        "status": session[7]
    }


# ============================================================
# CHECK SESSION EXPIRATION
# ============================================================

def check_session(
    session_id
):
    """
    Checks whether an attendance session
    is still active.
    """

    session = get_session(
        session_id
    )

    if session is None:
        return {
            "active": False,
            "status": "NOT_FOUND",
            "message": "Attendance session not found."
        }

    if session["status"] != "ACTIVE":
        return {
            "active": False,
            "status": session["status"],
            "message": "Attendance session is no longer active."
        }

    try:

        expires_at = datetime.strptime(
            session["expires_at"],
            "%Y-%m-%d %H:%M:%S"
        )

    except ValueError:

        return {
            "active": False,
            "status": "INVALID",
            "message": "Invalid session expiration time."
        }

    now = datetime.now()

    if now >= expires_at:

        expire_attendance_session(
            session_id
        )

        return {
            "active": False,
            "status": "EXPIRED",
            "message": "Attendance session has expired."
        }

    remaining_seconds = int(
        (
            expires_at - now
        ).total_seconds()
    )

    return {
        "active": True,
        "status": "ACTIVE",
        "message": "Attendance session is active.",
        "remaining_seconds": remaining_seconds
    }


# ============================================================
# VALIDATE ATTENDANCE SESSION QR
# ============================================================

def validate_session_qr(
    token,
    student_id
):
    """
    Validates an attendance session QR
    for a specific student.

    Checks:

    1. Session exists
    2. Session is active
    3. Session is not expired
    4. Student matches the class
    5. Student is enrolled
    """

    session = get_session_by_token(
        token
    )

    if session is None:
        return {
            "valid": False,
            "message": "Invalid attendance session QR."
        }

    session_check = check_session(
        session["id"]
    )

    if not session_check["active"]:

        return {
            "valid": False,
            "message": session_check["message"],
            "status": session_check["status"]
        }

    matching = validate_student_attendance(
        student_id,
        session["schedule_id"]
    )

    if not matching["matched"]:

        return {
            "valid": False,
            "message": matching["message"]
        }

    return {
        "valid": True,
        "message": "Attendance session verified.",
        "session": session,
        "student_id": student_id,
        "schedule_id": session["schedule_id"]
    }


# ============================================================
# CLOSE SESSION
# ============================================================

def close_session(
    session_id
):
    """
    Manually closes an attendance session.
    """

    session = get_session(
        session_id
    )

    if session is None:
        return False

    close_attendance_session(
        session_id
    )

    return True


# ============================================================
# GET QR FILE
# ============================================================

def get_qr_file(
    student_id,
    schedule_id
):
    """
    Returns the student's QR file path.
    """

    qr = get_student_qr(
        student_id,
        schedule_id
    )

    if qr is None:
        return None

    return qr[4]


# ============================================================
# CHECK QR FILE
# ============================================================

def qr_file_exists(
    filename
):
    """
    Checks whether a QR image file exists.
    """

    if not filename:
        return False

    return os.path.exists(
        filename
    )


# ============================================================
# OPEN QR IMAGE
# ============================================================

def open_qr_image(
    filename
):
    """
    Opens a QR image using PIL.
    """

    if not qr_file_exists(
        filename
    ):
        return None

    try:

        return Image.open(
            filename
        )

    except Exception:
        return None


# ============================================================
# DELETE QR FILE
# ============================================================

def delete_qr_file(
    filename
):
    """
    Deletes a QR image file.

    Database records are not deleted here.
    """

    if not filename:
        return False

    if not os.path.exists(
        filename
    ):
        return False

    try:

        os.remove(
            filename
        )

        return True

    except Exception:
        return False


# ============================================================
# QR TOKEN TYPE
# ============================================================

def get_qr_type(
    token
):
    """
    Identifies whether a token is a
    student QR or attendance session QR.
    """

    if not token:
        return "UNKNOWN"

    if token.startswith(
        STUDENT_QR_PREFIX
    ):
        return "STUDENT"

    if token.startswith(
        SESSION_QR_PREFIX
    ):
        return "ATTENDANCE_SESSION"

    return "UNKNOWN"


# ============================================================
# GENERAL QR VALIDATION
# ============================================================

def validate_qr_token(
    token
):
    """
    Identifies and validates a QR token.
    """

    qr_type = get_qr_type(
        token
    )

    if qr_type == "STUDENT":

        result = validate_student_qr(
            token
        )

        result["type"] = "STUDENT"

        return result

    if qr_type == "ATTENDANCE_SESSION":

        session = get_session_by_token(
            token
        )

        if session is None:
            return {
                "valid": False,
                "type": "ATTENDANCE_SESSION",
                "message": "Invalid attendance session QR."
            }

        session_check = check_session(
            session["id"]
        )

        return {
            "valid": session_check["active"],
            "type": "ATTENDANCE_SESSION",
            "status": session_check["status"],
            "message": session_check["message"],
            "session": session
        }

    return {
        "valid": False,
        "type": "UNKNOWN",
        "message": "Unknown QR code."
    }


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    print("ATTENDX QR SYSTEM")
    print("------------------")
    print("Student QR generation: READY")
    print("Student QR validation: READY")
    print("Attendance Session QR: READY")
    print("Session expiration: READY")
    print("QR token validation: READY")