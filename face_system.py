import os
import pickle
from datetime import datetime

import numpy as np
import face_recognition

from database import get_connection


# ============================================================
# FACE SYSTEM CONFIGURATION
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

FACE_FOLDER = os.path.join(
    BASE_DIR,
    "face_data"
)

FACE_FILE_EXTENSION = ".dat"

# Lower value = stricter face matching.
# This is facial distance, NOT image/pixel difference.
FACE_TOLERANCE = 0.50


# ============================================================
# FACE DATA FOLDER
# ============================================================

def create_face_folder():
    os.makedirs(
        FACE_FOLDER,
        exist_ok=True
    )


# ============================================================
# FACE DATABASE TABLE
# ============================================================

def create_face_table():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS face_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER UNIQUE NOT NULL,
            encoding_file TEXT NOT NULL,
            registered_at TEXT NOT NULL,

            FOREIGN KEY (student_id)
                REFERENCES students(id)
        )
    """)

    connection.commit()
    connection.close()


# ============================================================
# FACE FILE PATH
# ============================================================

def get_face_file(student_id):
    create_face_folder()

    return os.path.join(
        FACE_FOLDER,
        "student_" + str(student_id) + FACE_FILE_EXTENSION
    )


# ============================================================
# CHECK REGISTRATION
# ============================================================

def is_face_registered(student_id):

    create_face_table()

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id
        FROM face_data
        WHERE student_id = ?
    """, (student_id,))

    result = cursor.fetchone()

    connection.close()

    return result is not None


# ============================================================
# GET REGISTRATION INFORMATION
# ============================================================

def get_face_registration(student_id):

    create_face_table()

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
    """, (student_id,))

    registration = cursor.fetchone()

    connection.close()

    return registration


# ============================================================
# SAVE FACE TEMPLATE
# ============================================================

def save_face_template(
    student_id,
    face_encoding
):

    create_face_folder()
    create_face_table()

    filename = get_face_file(student_id)

    try:

        face_encoding = np.asarray(
            face_encoding,
            dtype=np.float64
        )

        if face_encoding.shape != (128,):
            return {
                "success": False,
                "message": "Invalid facial encoding."
            }

        face_data = {
            "student_id": student_id,
            "face_encoding": face_encoding.tolist(),
            "registered_at": datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        }

        with open(
            filename,
            "wb"
        ) as file:

            pickle.dump(
                face_data,
                file
            )

    except Exception as error:

        return {
            "success": False,
            "message": (
                "Unable to save face template: "
                + str(error)
            )
        }

    registered_at = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            INSERT INTO face_data
            (
                student_id,
                encoding_file,
                registered_at
            )
            VALUES (?, ?, ?)

            ON CONFLICT(student_id)
            DO UPDATE SET
                encoding_file = excluded.encoding_file,
                registered_at = excluded.registered_at
        """, (
            student_id,
            filename,
            registered_at
        ))

        connection.commit()
        connection.close()

        return {
            "success": True,
            "student_id": student_id,
            "encoding_file": filename,
            "registered_at": registered_at,
            "message": "Face template saved successfully."
        }

    except Exception as error:

        connection.close()

        return {
            "success": False,
            "message": (
                "Unable to save face registration: "
                + str(error)
            )
        }


# ============================================================
# LOAD FACE TEMPLATE
# ============================================================

def load_face_template(student_id):

    registration = get_face_registration(
        student_id
    )

    if registration is None:
        return None

    filename = registration[2]

    if not os.path.exists(filename):
        return None

    try:

        with open(
            filename,
            "rb"
        ) as file:

            data = pickle.load(file)

        # NEW FORMAT
        if isinstance(data, dict):

            if "face_encoding" not in data:
                return None

            encoding = np.asarray(
                data["face_encoding"],
                dtype=np.float64
            )

        # Direct encoding format
        else:

            encoding = np.asarray(
                data,
                dtype=np.float64
            )

        if encoding.shape != (128,):
            return None

        return encoding

    except Exception:

        return None


# ============================================================
# DELETE FACE TEMPLATE
# ============================================================

def delete_face_registration(student_id):

    registration = get_face_registration(
        student_id
    )

    if registration is None:

        return {
            "success": False,
            "message": "Face registration not found."
        }

    filename = registration[2]

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        DELETE FROM face_data
        WHERE student_id = ?
    """, (student_id,))

    connection.commit()
    connection.close()

    file_deleted = False

    if os.path.exists(filename):

        try:

            os.remove(filename)
            file_deleted = True

        except Exception:

            file_deleted = False

    return {
        "success": True,
        "file_deleted": file_deleted,
        "message": "Face registration deleted."
    }


# ============================================================
# FACE ENCODING VALIDATION
# ============================================================

def is_valid_face_encoding(encoding):

    if encoding is None:
        return False

    try:

        encoding = np.asarray(
            encoding,
            dtype=np.float64
        )

        return encoding.shape == (128,)

    except Exception:

        return False


# ============================================================
# REGISTER FACE ENCODING
# ============================================================

def register_face_encoding(
    student_id,
    encoding
):

    if student_id is None:

        return {
            "success": False,
            "message": "Student ID is required."
        }

    if not is_valid_face_encoding(encoding):

        return {
            "success": False,
            "message": "Invalid face encoding."
        }

    return save_face_template(
        student_id,
        encoding
    )


# ============================================================
# COMPARE FACE ENCODINGS
# ============================================================

def compare_face_encodings(
    known_encoding,
    captured_encoding
):

    if not is_valid_face_encoding(
        known_encoding
    ):
        return False

    if not is_valid_face_encoding(
        captured_encoding
    ):
        return False

    try:

        known_encoding = np.asarray(
            known_encoding,
            dtype=np.float64
        )

        captured_encoding = np.asarray(
            captured_encoding,
            dtype=np.float64
        )

        distance = face_recognition.face_distance(
            [known_encoding],
            captured_encoding
        )[0]

        return float(distance) <= FACE_TOLERANCE

    except Exception:

        return False


# ============================================================
# GET FACE DISTANCE
# ============================================================

def get_face_distance(
    known_encoding,
    captured_encoding
):

    if not is_valid_face_encoding(
        known_encoding
    ):
        return None

    if not is_valid_face_encoding(
        captured_encoding
    ):
        return None

    try:

        known_encoding = np.asarray(
            known_encoding,
            dtype=np.float64
        )

        captured_encoding = np.asarray(
            captured_encoding,
            dtype=np.float64
        )

        distance = face_recognition.face_distance(
            [known_encoding],
            captured_encoding
        )[0]

        return float(distance)

    except Exception:

        return None


# ============================================================
# VERIFY STUDENT FACE
# ============================================================

def verify_student_face(
    student_id,
    captured_encoding
):

    known_encoding = load_face_template(
        student_id
    )

    if known_encoding is None:

        return {
            "verified": False,
            "message": "Student has no registered face."
        }

    if captured_encoding is None:

        return {
            "verified": False,
            "message": "No captured face was provided."
        }

    distance = get_face_distance(
        known_encoding,
        captured_encoding
    )

    if distance is None:

        return {
            "verified": False,
            "message": "Invalid face encoding."
        }

    matched = distance <= FACE_TOLERANCE

    if matched:

        return {
            "verified": True,
            "student_id": student_id,
            "distance": distance,
            "message": "Face verified successfully."
        }

    return {
        "verified": False,
        "distance": distance,
        "message": "Face verification failed."
    }


# ============================================================
# FIND STUDENT BY FACE
# ============================================================

def find_student_by_face(
    captured_encoding
):

    if not is_valid_face_encoding(
        captured_encoding
    ):

        return {
            "found": False,
            "message": "Invalid captured face."
        }

    create_face_table()

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            student_id,
            encoding_file
        FROM face_data
    """)

    registrations = cursor.fetchall()

    connection.close()

    best_student_id = None
    best_distance = None

    for registration in registrations:

        student_id = registration[0]

        known_encoding = load_face_template(
            student_id
        )

        if known_encoding is None:
            continue

        distance = get_face_distance(
            known_encoding,
            captured_encoding
        )

        if distance is None:
            continue

        if (
            best_distance is None
            or distance < best_distance
        ):

            best_distance = distance
            best_student_id = student_id

    if (
        best_student_id is not None
        and best_distance <= FACE_TOLERANCE
    ):

        return {
            "found": True,
            "student_id": best_student_id,
            "distance": best_distance,
            "message": "Student face identified."
        }

    return {
        "found": False,
        "distance": best_distance,
        "message": "No matching student face found."
    }


# ============================================================
# FACE ATTENDANCE VALIDATION
# ============================================================

def validate_face_attendance(
    student_id,
    schedule_id
):

    from matching import (
        validate_student_attendance
    )

    validation = validate_student_attendance(
        student_id,
        schedule_id
    )

    if not validation["matched"]:

        return {
            "valid": False,
            "message": validation["message"]
        }

    return {
        "valid": True,
        "student_id": student_id,
        "schedule_id": schedule_id,
        "message": "Face attendance validation successful."
    }


# ============================================================
# CAMERA INTERFACE
# ============================================================

def camera_available():

    try:

        import cv2

        return True

    except ImportError:

        return False


def open_camera():

    try:

        import cv2

    except ImportError:

        return {
            "success": False,
            "message": "OpenCV is not installed yet."
        }

    try:

        camera = cv2.VideoCapture(0)

        if not camera.isOpened():

            return {
                "success": False,
                "message": "Unable to open camera."
            }

        return {
            "success": True,
            "camera": camera,
            "message": "Camera opened successfully."
        }

    except Exception as error:

        return {
            "success": False,
            "message": "Camera error: " + str(error)
        }


def close_camera(camera):

    if camera is None:
        return

    try:

        camera.release()

    except Exception:

        pass


# ============================================================
# FACE REGISTRATION STATUS
# ============================================================

def get_face_status(student_id):

    registration = get_face_registration(
        student_id
    )

    if registration is None:

        return {
            "registered": False,
            "message": "FACE NOT REGISTERED"
        }

    filename = registration[2]

    if not os.path.exists(filename):

        return {
            "registered": False,
            "message": "FACE DATA FILE MISSING"
        }

    encoding = load_face_template(
        student_id
    )

    if encoding is None:

        return {
            "registered": False,
            "message": "OLD FACE DATA - RE-REGISTER REQUIRED"
        }

    return {
        "registered": True,
        "message": "FACE REGISTERED",
        "registered_at": registration[3]
    }


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    create_face_folder()
    create_face_table()

    print("ATTENDX FACE SYSTEM")
    print("--------------------")
    print("Face data folder: READY")
    print("Face database table: READY")
    print("Face encoding engine: READY")
    print("Facial feature comparison: READY")
    print("Camera interface: READY")
    print()
    print(
        "Matching method: FACIAL ENCODINGS"
    )
    print(
        "Pixel/image comparison: DISABLED"
    )
    print(
        "Tolerance:",
        FACE_TOLERANCE
    )