import cv2
import os
import pickle
from datetime import datetime

from database import get_connection


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEACHER_FACE_FOLDER = os.path.join(
    BASE_DIR,
    "teacher_face_data"
)


def create_teacher_face_folder():
    os.makedirs(
        TEACHER_FACE_FOLDER,
        exist_ok=True
    )


def create_teacher_face_table():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS teacher_face_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            teacher_id INTEGER UNIQUE NOT NULL,
            encoding_file TEXT NOT NULL,
            registered_at TEXT NOT NULL,
            FOREIGN KEY (teacher_id)
                REFERENCES teachers(id)
        )
    """)

    connection.commit()
    connection.close()


def get_teacher(teacher_id):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id, teacher_id, name
        FROM teachers
        WHERE id = ?
    """, (teacher_id,))

    teacher = cursor.fetchone()

    connection.close()

    return teacher


def save_teacher_face_registration(
    teacher_id,
    face_data
):
    create_teacher_face_folder()
    create_teacher_face_table()

    face_file = os.path.join(
        TEACHER_FACE_FOLDER,
        "teacher_" + str(teacher_id) + ".pkl"
    )

    with open(face_file, "wb") as file:
        pickle.dump(
            face_data,
            file
        )

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT OR REPLACE INTO teacher_face_data
        (
            teacher_id,
            encoding_file,
            registered_at
        )
        VALUES (?, ?, ?)
    """, (
        teacher_id,
        face_file,
        datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    ))

    connection.commit()
    connection.close()


def register_teacher_face(teacher_id):

    teacher = get_teacher(teacher_id)

    if teacher is None:
        print("Teacher not found.")
        return False

    create_teacher_face_folder()
    create_teacher_face_table()

    camera = cv2.VideoCapture(0)

    if not camera.isOpened():
        print("Camera: NOT AVAILABLE")
        return False

    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades +
        "haarcascade_frontalface_default.xml"
    )

    if face_cascade.empty():
        print("Face detector: NOT AVAILABLE")
        camera.release()
        return False

    print()
    print("ATTENDX TEACHER FACE REGISTRATION")
    print("----------------------------------")
    print("Teacher:", teacher[2])
    print()
    print("Camera: READY")
    print("Look directly at the camera.")
    print("Press S to save your face.")
    print("Press Q to cancel.")
    print()

    captured_face = None

    while True:

        success, frame = camera.read()

        if not success:
            print("Failed to read camera.")
            break

        gray = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2GRAY
        )

        faces = face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(100, 100)
        )

        if len(faces) == 1:

            x, y, width, height = faces[0]

            cv2.rectangle(
                frame,
                (x, y),
                (x + width, y + height),
                (0, 255, 0),
                2
            )

            cv2.putText(
                frame,
                "FACE READY - PRESS S",
                (x, y - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2
            )

            face_crop = gray[
                y:y + height,
                x:x + width
            ]

            captured_face = cv2.resize(
                face_crop,
                (200, 200)
            )

        elif len(faces) > 1:

            cv2.putText(
                frame,
                "ONLY ONE FACE ALLOWED",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 0, 255),
                2
            )

            captured_face = None

        else:

            cv2.putText(
                frame,
                "NO FACE DETECTED",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 0, 255),
                2
            )

            captured_face = None

        cv2.imshow(
            "ATTENDX Teacher Face Registration",
            frame
        )

        key = cv2.waitKey(1) & 0xFF

        if key == ord("s"):

            if captured_face is None:
                print(
                    "Cannot save. Make sure exactly one face is visible."
                )
                continue

            face_data = {
                "teacher_id": teacher_id,
                "face_image": captured_face.tolist(),
                "registered_at": datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            }

            save_teacher_face_registration(
                teacher_id,
                face_data
            )

            print()
            print("TEACHER FACE REGISTRATION SUCCESSFUL")
            print("Teacher:", teacher[2])
            print()

            camera.release()
            cv2.destroyAllWindows()

            return True

        if key == ord("q"):

            print("Teacher face registration cancelled.")

            break

    camera.release()
    cv2.destroyAllWindows()

    return False
