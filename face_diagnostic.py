import cv2
import face_recognition
import numpy as np

from face_system import (
    load_face_template,
    get_face_distance,
    FACE_TOLERANCE
)


def run_face_test():

    print()
    print("ATTENDX REAL FACE RECOGNITION TEST")
    print("----------------------------------")
    print("Tolerance:", FACE_TOLERANCE)
    print()
    print("Look at the camera.")
    print("Press S to test the captured face.")
    print("Press Q to quit.")
    print()

    camera = cv2.VideoCapture(0)

    if not camera.isOpened():
        print("ERROR: Camera could not be opened.")
        return

    captured_encoding = None

    while True:

        success, frame = camera.read()

        if not success:
            print("ERROR: Could not read camera.")
            break

        rgb_frame = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB
        )

        locations = face_recognition.face_locations(
            rgb_frame,
            model="hog"
        )

        encodings = face_recognition.face_encodings(
            rgb_frame,
            locations
        )

        if len(encodings) == 1:

            captured_encoding = encodings[0]

            top, right, bottom, left = locations[0]

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
                (left, max(top - 10, 25)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2
            )

        elif len(encodings) > 1:

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
            "ATTENDX Real Face Test",
            frame
        )

        key = cv2.waitKey(1) & 0xFF

        if key == ord("s"):

            if captured_encoding is None:

                print(
                    "Cannot test. Make sure exactly one face is visible."
                )
                continue

            print()
            print("CAPTURED FACE ENCODING: READY")
            print()

            test_student(
                1,
                captured_encoding
            )

            test_student(
                2,
                captured_encoding
            )

            camera.release()
            cv2.destroyAllWindows()

            return

        if key == ord("q"):

            break

    camera.release()
    cv2.destroyAllWindows()


def test_student(
    student_id,
    captured_encoding
):

    known_encoding = load_face_template(
        student_id
    )

    print(
        "Student database ID:",
        student_id
    )

    if known_encoding is None:

        print("  Face encoding: NOT AVAILABLE")
        print()

        return

    distance = get_face_distance(
        known_encoding,
        captured_encoding
    )

    if distance is None:

        print("  Distance: ERROR")
        print()

        return

    print(
        "  Face distance:",
        round(distance, 6)
    )

    print(
        "  Tolerance:",
        FACE_TOLERANCE
    )

    if distance <= FACE_TOLERANCE:

        print(
            "  RESULT: MATCH"
        )

    else:

        print(
            "  RESULT: NO MATCH"
        )

    print()


if __name__ == "__main__":

    run_face_test()