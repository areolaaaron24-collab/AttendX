import cv2
import numpy as np
import face_recognition


def detect_faces():
    print("ATTENDX FACE DETECTION")
    print("----------------------")

    camera = cv2.VideoCapture(0)

    if not camera.isOpened():
        print("Camera: NOT AVAILABLE")
        return

    print("Camera: READY")
    print("Face recognition engine: READY")
    print("Facial feature encoding: READY")
    print("Press Q to close.")

    while True:
        success, frame = camera.read()

        if not success:
            print("Failed to read camera.")
            break

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        face_locations = face_recognition.face_locations(
            rgb_frame,
            model="hog"
        )

        face_encodings = face_recognition.face_encodings(
            rgb_frame,
            face_locations
        )

        for location, encoding in zip(face_locations, face_encodings):

            top, right, bottom, left = location

            cv2.rectangle(
                frame,
                (left, top),
                (right, bottom),
                (255, 255, 255),
                2
            )

            cv2.putText(
                frame,
                "FACE ENCODING READY",
                (left, top - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2
            )

        cv2.imshow(
            "ATTENDX Face Recognition",
            frame
        )

        key = cv2.waitKey(1) & 0xFF

        if key == ord("q"):
            break

    camera.release()
    cv2.destroyAllWindows()


def get_face_encoding(frame):
    """
    Convert one camera frame into a 128-dimensional
    facial feature encoding.

    Returns:
        numpy array with shape (128,)
        or None if no valid face is found.
    """

    if frame is None:
        return None

    rgb_frame = cv2.cvtColor(
        frame,
        cv2.COLOR_BGR2RGB
    )

    face_locations = face_recognition.face_locations(
        rgb_frame,
        model="hog"
    )

    if len(face_locations) == 0:
        return None

    if len(face_locations) > 1:
        return None

    encodings = face_recognition.face_encodings(
        rgb_frame,
        face_locations
    )

    if len(encodings) == 0:
        return None

    encoding = np.asarray(
        encodings[0],
        dtype=np.float64
    )

    if encoding.shape != (128,):
        return None

    return encoding


def get_face_encodings(frame):
    """
    Detect all faces in a frame and return their
    128-dimensional facial feature encodings.
    """

    if frame is None:
        return []

    rgb_frame = cv2.cvtColor(
        frame,
        cv2.COLOR_BGR2RGB
    )

    face_locations = face_recognition.face_locations(
        rgb_frame,
        model="hog"
    )

    if len(face_locations) == 0:
        return []

    encodings = face_recognition.face_encodings(
        rgb_frame,
        face_locations
    )

    valid_encodings = []

    for encoding in encodings:

        encoding = np.asarray(
            encoding,
            dtype=np.float64
        )

        if encoding.shape == (128,):
            valid_encodings.append(encoding)

    return valid_encodings


def compare_faces(known_encoding, captured_encoding, tolerance=0.50):
    """
    Compare two real facial feature encodings.

    This does NOT compare the background or raw pixels.

    Returns:
        True  = same face within tolerance
        False = different face
    """

    try:
        known = np.asarray(
            known_encoding,
            dtype=np.float64
        )

        captured = np.asarray(
            captured_encoding,
            dtype=np.float64
        )

        if known.shape != (128,):
            return False

        if captured.shape != (128,):
            return False

        distance = face_recognition.face_distance(
            [known],
            captured
        )[0]

        return float(distance) <= tolerance

    except Exception:
        return False


def get_face_distance(known_encoding, captured_encoding):
    """
    Return the facial feature distance between
    two face encodings.
    """

    try:
        known = np.asarray(
            known_encoding,
            dtype=np.float64
        )

        captured = np.asarray(
            captured_encoding,
            dtype=np.float64
        )

        if known.shape != (128,):
            return None

        if captured.shape != (128,):
            return None

        distance = face_recognition.face_distance(
            [known],
            captured
        )[0]

        return float(distance)

    except Exception:
        return None


if __name__ == "__main__":
    detect_faces()