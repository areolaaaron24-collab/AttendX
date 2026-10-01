import cv2
import os
import pickle
from datetime import datetime

import face_recognition
import numpy as np

from database import get_connection
from face_system import (
    create_face_folder,
    create_face_table,
    load_face_template,
    get_face_distance,
    FACE_TOLERANCE
)


BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

FACE_FOLDER = os.path.join(
    BASE_DIR,
    "face_data"
)


# ============================================================
# GET STUDENT
# ============================================================

def get_student(student_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT id, school_id, name, course, year, section
        FROM students
        WHERE id = ?
        """,
        (student_id,)
    )

    student = cursor.fetchone()

    connection.close()

    return student


# ============================================================
# GET ALL REGISTERED FACE ENCODINGS
# ============================================================

def get_registered_face_encodings():

    create_face_table()

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT student_id
        FROM face_data
        """
    )

    rows = cursor.fetchall()

    connection.close()

    registered_faces = []

    for row in rows:

        student_id = row[0]

        encoding = load_face_template(
            student_id
        )

        if encoding is None:
            continue

        registered_faces.append(
            (
                student_id,
                encoding
            )
        )

    return registered_faces


# ============================================================
# CHECK DUPLICATE FACE
# ============================================================

def check_duplicate_face(
    student_id,
    new_encoding
):

    registered_faces = get_registered_face_encodings()

    for registered_student_id, known_encoding in registered_faces:

        # Allow the current student to update their own face.
        if registered_student_id == student_id:
            continue

        distance = get_face_distance(
            known_encoding,
            new_encoding
        )

        if distance is None:
            continue

        # Use a stricter duplicate threshold.
        # This prevents the same face from being
        # registered to multiple students.
        duplicate_tolerance = 0.45

        if distance <= duplicate_tolerance:

            return {
                "duplicate": True,
                "student_id": registered_student_id,
                "distance": distance,
                "message": (
                    "This face is already registered "
                    "to another student."
                )
            }

    return {
        "duplicate": False,
        "message": "Face is available for registration."
    }


# ============================================================
# SAVE FACE REGISTRATION
# ============================================================

def save_face_registration(
    student_id,
    face_data
):

    create_face_folder()
    create_face_table()

    face_file = os.path.join(
        FACE_FOLDER,
        "student_" + str(student_id) + ".dat"
    )

    try:

        with open(
            face_file,
            "wb"
        ) as file:

            pickle.dump(
                face_data,
                file
            )

    except Exception as error:

        print(
            "Unable to save face:",
            error
        )

        return None

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute(
            """
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
            """,
            (
                student_id,
                face_file,
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            )
        )

        connection.commit()
        connection.close()

        return face_file

    except Exception as error:

        connection.close()

        print(
            "Unable to save database record:",
            error
        )

        return None


# ============================================================
# REGISTER STUDENT FACE
# ============================================================

def register_student_face(
    student_id
):

    student = get_student(
        student_id
    )

    if student is None:

        print(
            "Student not found."
        )

        return False

    print()
    print(
        "ATTENDX FACE REGISTRATION"
    )
    print(
        "-------------------------"
    )

    print(
        "Student ID:",
        student[1]
    )

    print(
        "Name:",
        student[2]
    )

    print(
        "Course:",
        student[3]
    )

    print(
        "Year:",
        student[4]
    )

    print(
        "Section:",
        student[5]
    )

    print()

    print(
        "Starting camera..."
    )

    camera = cv2.VideoCapture(0)

    if not camera.isOpened():

        print(
            "Camera: NOT AVAILABLE"
        )

        return False

    print(
        "Camera: READY"
    )

    print(
        "Look directly at the camera."
    )

    print(
        "Press S to register."
    )

    print(
        "Press Q to cancel."
    )

    print()

    captured_encoding = None

    while True:

        success, frame = camera.read()

        if not success:

            print(
                "Failed to read camera."
            )

            break

        rgb_frame = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB
        )

        face_locations = (
            face_recognition.face_locations(
                rgb_frame,
                model="hog"
            )
        )

        face_encodings = (
            face_recognition.face_encodings(
                rgb_frame,
                face_locations
            )
        )

        if len(face_encodings) == 1:

            captured_encoding = (
                face_encodings[0]
            )

            top, right, bottom, left = (
                face_locations[0]
            )

            cv2.rectangle(
                frame,
                (left, top),
                (right, bottom),
                (255, 255, 255),
                2
            )

            cv2.putText(
                frame,
                "FACE READY - PRESS S",
                (
                    left,
                    max(top - 10, 25)
                ),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2
            )

        elif len(face_encodings) > 1:

            captured_encoding = None

            cv2.putText(
                frame,
                "ONLY ONE FACE ALLOWED",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (255, 255, 255),
                2
            )

        else:

            captured_encoding = None

            cv2.putText(
                frame,
                "NO FACE DETECTED",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (255, 255, 255),
                2
            )

        cv2.imshow(
            "ATTENDX Face Registration",
            frame
        )

        key = cv2.waitKey(1) & 0xFF

        # ====================================================
        # SAVE
        # ====================================================

        if key == ord("s"):

            if captured_encoding is None:

                print(
                    "Cannot register."
                )

                print(
                    "Make sure exactly one face is visible."
                )

                continue

            print()

            print(
                "Checking face..."
            )

            duplicate_result = (
                check_duplicate_face(
                    student_id,
                    captured_encoding
                )
            )

            if duplicate_result["duplicate"]:

                duplicate_student_id = (
                    duplicate_result["student_id"]
                )

                distance = (
                    duplicate_result["distance"]
                )

                print()
                print(
                    "FACE REGISTRATION BLOCKED"
                )

                print(
                    "This face is already registered."
                )

                print(
                    "Existing database student ID:",
                    duplicate_student_id
                )

                print(
                    "Face distance:",
                    round(distance, 6)
                )

                print(
                    "Duplicate tolerance:",
                    0.45
                )

                print()

                continue

            face_data = {

                "student_id": student_id,

                "face_encoding": (
                    captured_encoding.tolist()
                ),

                "registered_at": (
                    datetime.now().strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                )
            }

            saved_file = (
                save_face_registration(
                    student_id,
                    face_data
                )
            )

            if saved_file is None:

                print()
                print(
                    "FACE REGISTRATION FAILED"
                )

                continue

            print()
            print(
                "FACE REGISTRATION SUCCESSFUL"
            )

            print(
                "Student:",
                student[2]
            )

            print(
                "Student ID:",
                student[1]
            )

            print(
                "Encoding saved:",
                saved_file
            )

            print()

            camera.release()
            cv2.destroyAllWindows()

            return True

        # ====================================================
        # CANCEL
        # ====================================================

        if key == ord("q"):

            print(
                "Face registration cancelled."
            )

            break

    camera.release()
    cv2.destroyAllWindows()

    return False


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    create_face_folder()
    create_face_table()

    print(
        "ATTENDX FACE REGISTRATION TEST"
    )

    print(
        "-------------------------------"
    )

    student_id = input(
        "Enter database student ID: "
    )

    try:

        student_id = int(
            student_id
        )

    except ValueError:

        print(
            "Invalid student ID."
        )

        exit()

    register_student_face(
        student_id
    )