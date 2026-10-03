import cv2
import os
import pickle
import time
import threading
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


# ============================================================
# ATTENDX FACE REGISTRATION
# STUDENT FACE REGISTRATION
# SMOOTH + CLEAR VERSION
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

FACE_FOLDER = os.path.join(
    BASE_DIR,
    "face_data"
)


# ============================================================
# CAMERA CONFIGURATION
# ============================================================

CAMERA_INDEX = 0

CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480

MIN_DETECTION_WIDTH = 320
NORMAL_DETECTION_WIDTH = 400
MAX_DETECTION_WIDTH = 480

NORMAL_DETECTION_INTERVAL = 2
LOW_DETECTION_INTERVAL = 3
HIGH_DETECTION_INTERVAL = 2

MIN_FACE_WIDTH = 90
MIN_FACE_HEIGHT = 90

DUPLICATE_TOLERANCE = 0.45

ENCODING_JITTERS = 1


# ============================================================
# UI CONFIGURATION
# ============================================================

WINDOW_NAME = "ATTENDX Face Registration"

WINDOW_WIDTH = 760
WINDOW_HEIGHT = 650

BUTTON_HEIGHT = 48

BG_COLOR = (8, 11, 22)
CARD_COLOR = (17, 23, 41)

PURPLE = (252, 92, 124)
PURPLE_DARK = (234, 73, 105)

WHITE = (255, 255, 255)
LIGHT_GRAY = (210, 210, 210)

GREEN = (90, 220, 120)
RED = (80, 90, 240)
YELLOW = (80, 220, 255)


# ============================================================
# GLOBAL UI STATE
# ============================================================

register_clicked = False
cancel_clicked = False

ui_lock = threading.Lock()

last_detection = []
last_detection_frame = -1

current_detection_width = NORMAL_DETECTION_WIDTH
current_detection_interval = NORMAL_DETECTION_INTERVAL

performance_mode = "NORMAL"

fps_value = 0.0

last_status = "LOOK AT THE CAMERA"
status_type = "normal"


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

        # Allow current student to update
        # their own registered face.
        if registered_student_id == student_id:
            continue

        distance = get_face_distance(
            known_encoding,
            new_encoding
        )

        if distance is None:
            continue

        if distance <= DUPLICATE_TOLERANCE:

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
# BUTTON CALLBACKS
# ============================================================

def register_button_callback(
    event,
    x,
    y,
    flags,
    param
):

    global register_clicked
    global cancel_clicked

    if event != cv2.EVENT_LBUTTONDOWN:
        return

    # --------------------------------------------------------
    # REGISTER BUTTON
    # --------------------------------------------------------

    if (
        param is not None
        and "register_button" in param
    ):

        button = param["register_button"]

        x1 = button[0]
        y1 = button[1]
        x2 = button[2]
        y2 = button[3]

        if (
            x1 <= x <= x2
            and y1 <= y <= y2
        ):

            with ui_lock:
                register_clicked = True

            return

    # --------------------------------------------------------
    # CANCEL BUTTON
    # --------------------------------------------------------

    if (
        param is not None
        and "cancel_button" in param
    ):

        button = param["cancel_button"]

        x1 = button[0]
        y1 = button[1]
        x2 = button[2]
        y2 = button[3]

        if (
            x1 <= x <= x2
            and y1 <= y <= y2
        ):

            with ui_lock:
                cancel_clicked = True


# ============================================================
# SET STATUS
# ============================================================

def set_status(
    message,
    status="normal"
):

    global last_status
    global status_type

    last_status = message
    status_type = status


# ============================================================
# GET PERFORMANCE SETTINGS
# ============================================================

def get_performance_settings():

    return (
        current_detection_width,
        current_detection_interval,
        performance_mode
    )


# ============================================================
# ADAPTIVE PERFORMANCE CONTROLLER
# ============================================================

class AdaptivePerformance:

    def __init__(self):

        self.fps_samples = []

        self.last_update = time.perf_counter()

        self.low_counter = 0
        self.high_counter = 0

    def update(
        self,
        fps
    ):

        global current_detection_width
        global current_detection_interval
        global performance_mode

        if fps <= 0:
            return

        self.fps_samples.append(
            fps
        )

        if len(self.fps_samples) > 20:

            self.fps_samples.pop(
                0
            )

        average_fps = (
            sum(self.fps_samples)
            /
            len(self.fps_samples)
        )

        # ----------------------------------------------------
        # LOW PERFORMANCE
        # ----------------------------------------------------

        if average_fps < 17:

            self.low_counter += 1
            self.high_counter = 0

        # ----------------------------------------------------
        # HIGH PERFORMANCE
        # ----------------------------------------------------

        elif average_fps > 27:

            self.high_counter += 1
            self.low_counter = 0

        else:

            self.low_counter = 0
            self.high_counter = 0

        # ----------------------------------------------------
        # Reduce detection workload
        # ----------------------------------------------------

        if self.low_counter >= 10:

            if current_detection_width > MIN_DETECTION_WIDTH:

                current_detection_width = (
                    current_detection_width - 40
                )

                if current_detection_width < MIN_DETECTION_WIDTH:

                    current_detection_width = (
                        MIN_DETECTION_WIDTH
                    )

            current_detection_interval = (
                LOW_DETECTION_INTERVAL
            )

            performance_mode = "LOW"

            self.low_counter = 0

        # ----------------------------------------------------
        # Increase detection quality
        # ----------------------------------------------------

        elif self.high_counter >= 15:

            if current_detection_width < MAX_DETECTION_WIDTH:

                current_detection_width = (
                    current_detection_width + 40
                )

                if current_detection_width > MAX_DETECTION_WIDTH:

                    current_detection_width = (
                        MAX_DETECTION_WIDTH
                    )

            current_detection_interval = (
                HIGH_DETECTION_INTERVAL
            )

            performance_mode = "HIGH"

            self.high_counter = 0

        else:

            if (
                current_detection_width
                ==
                NORMAL_DETECTION_WIDTH
            ):

                current_detection_interval = (
                    NORMAL_DETECTION_INTERVAL
                )

                performance_mode = "NORMAL"


# ============================================================
# CREATE CAMERA
# ============================================================

def create_camera():

    camera = None

    # --------------------------------------------------------
    # Try DirectShow first on Windows.
    # --------------------------------------------------------

    try:

        camera = cv2.VideoCapture(
            CAMERA_INDEX,
            cv2.CAP_DSHOW
        )

    except Exception:

        camera = None

    # --------------------------------------------------------
    # Fallback
    # --------------------------------------------------------

    if (
        camera is None
        or not camera.isOpened()
    ):

        if camera is not None:
            camera.release()

        camera = cv2.VideoCapture(
            CAMERA_INDEX
        )

    if not camera.isOpened():

        return None

    # --------------------------------------------------------
    # Camera resolution
    # --------------------------------------------------------

    camera.set(
        cv2.CAP_PROP_FRAME_WIDTH,
        CAMERA_WIDTH
    )

    camera.set(
        cv2.CAP_PROP_FRAME_HEIGHT,
        CAMERA_HEIGHT
    )

    # --------------------------------------------------------
    # Reduce camera buffering when supported.
    # --------------------------------------------------------

    try:

        camera.set(
            cv2.CAP_PROP_BUFFERSIZE,
            1
        )

    except Exception:
        pass

    # --------------------------------------------------------
    # Try 30 FPS.
    # --------------------------------------------------------

    try:

        camera.set(
            cv2.CAP_PROP_FPS,
            30
        )

    except Exception:
        pass

    return camera


# ============================================================
# PREPARE DETECTION FRAME
# ============================================================

def prepare_detection_frame(
    frame,
    target_width
):

    height, width = frame.shape[:2]

    if width <= target_width:

        return frame, 1.0

    scale = (
        target_width
        /
        float(width)
    )

    target_height = int(
        height * scale
    )

    resized = cv2.resize(
        frame,
        (
            target_width,
            target_height
        ),
        interpolation=cv2.INTER_AREA
    )

    return resized, scale


# ============================================================
# DETECT FACES
# ============================================================

def detect_faces(
    frame
):

    target_width = (
        current_detection_width
    )

    detection_frame, scale = (
        prepare_detection_frame(
            frame,
            target_width
        )
    )

    rgb_frame = cv2.cvtColor(
        detection_frame,
        cv2.COLOR_BGR2RGB
    )

    locations_small = (
        face_recognition.face_locations(
            rgb_frame,
            model="hog"
        )
    )

    if not locations_small:

        return []

    if scale == 1.0:

        return locations_small

    locations_original = []

    inverse_scale = (
        1.0
        /
        scale
    )

    for location in locations_small:

        top, right, bottom, left = location

        top = int(
            top * inverse_scale
        )

        right = int(
            right * inverse_scale
        )

        bottom = int(
            bottom * inverse_scale
        )

        left = int(
            left * inverse_scale
        )

        locations_original.append(
            (
                top,
                right,
                bottom,
                left
            )
        )

    return locations_original


# ============================================================
# VALIDATE FACE POSITION
# ============================================================

def validate_face_position(
    frame,
    face_location
):

    height, width = frame.shape[:2]

    top, right, bottom, left = (
        face_location
    )

    face_width = (
        right - left
    )

    face_height = (
        bottom - top
    )

    # --------------------------------------------------------
    # Face must be large enough.
    # --------------------------------------------------------

    if (
        face_width < MIN_FACE_WIDTH
        or
        face_height < MIN_FACE_HEIGHT
    ):

        return {
            "valid": False,
            "reason": "MOVE CLOSER"
        }

    # --------------------------------------------------------
    # Calculate center.
    # --------------------------------------------------------

    face_center_x = (
        left + right
    ) // 2

    face_center_y = (
        top + bottom
    ) // 2

    frame_center_x = (
        width // 2
    )

    frame_center_y = (
        height // 2
    )

    # --------------------------------------------------------
    # Allow reasonable movement around center.
    # --------------------------------------------------------

    horizontal_limit = (
        width * 0.32
    )

    vertical_limit = (
        height * 0.32
    )

    if abs(
        face_center_x - frame_center_x
    ) > horizontal_limit:

        return {
            "valid": False,
            "reason": "CENTER YOUR FACE"
        }

    if abs(
        face_center_y - frame_center_y
    ) > vertical_limit:

        return {
            "valid": False,
            "reason": "CENTER YOUR FACE"
        }

    return {
        "valid": True,
        "reason": "FACE READY"
    }


# ============================================================
# DRAW FACE BOX
# ============================================================

def draw_face_box(
    frame,
    location,
    valid=True
):

    top, right, bottom, left = (
        location
    )

    if valid:

        thickness = 2

        cv2.rectangle(
            frame,
            (left, top),
            (right, bottom),
            GREEN,
            thickness
        )

        corner = 16

        cv2.line(
            frame,
            (left, top),
            (left + corner, top),
            GREEN,
            4
        )

        cv2.line(
            frame,
            (left, top),
            (left, top + corner),
            GREEN,
            4
        )

        cv2.line(
            frame,
            (right, top),
            (right - corner, top),
            GREEN,
            4
        )

        cv2.line(
            frame,
            (right, top),
            (right, top + corner),
            GREEN,
            4
        )

        cv2.line(
            frame,
            (left, bottom),
            (left + corner, bottom),
            GREEN,
            4
        )

        cv2.line(
            frame,
            (left, bottom),
            (left, bottom - corner),
            GREEN,
            4
        )

        cv2.line(
            frame,
            (right, bottom),
            (right - corner, bottom),
            GREEN,
            4
        )

        cv2.line(
            frame,
            (right, bottom),
            (right, bottom - corner),
            GREEN,
            4
        )

    else:

        cv2.rectangle(
            frame,
            (left, top),
            (right, bottom),
            YELLOW,
            2
        )


# ============================================================
# DRAW TEXT WITH BACKGROUND
# ============================================================

def draw_text_box(
    frame,
    text,
    position,
    scale=0.6,
    color=WHITE,
    thickness=2
):

    x, y = position

    font = cv2.FONT_HERSHEY_SIMPLEX

    (
        text_width,
        text_height
    ), baseline = cv2.getTextSize(
        text,
        font,
        scale,
        thickness
    )

    padding = 8

    cv2.rectangle(
        frame,
        (
            x - padding,
            y - text_height - padding
        ),
        (
            x + text_width + padding,
            y + baseline + padding
        ),
        BG_COLOR,
        -1
    )

    cv2.putText(
        frame,
        text,
        (x, y),
        font,
        scale,
        color,
        thickness,
        cv2.LINE_AA
    )


# ============================================================
# DRAW BUTTON
# ============================================================

def draw_button(
    frame,
    rectangle,
    text,
    active=True
):

    x1, y1, x2, y2 = rectangle

    if active:

        fill_color = PURPLE

    else:

        fill_color = (
            70,
            70,
            80
        )

    cv2.rectangle(
        frame,
        (x1, y1),
        (x2, y2),
        fill_color,
        -1
    )

    cv2.rectangle(
        frame,
        (x1, y1),
        (x2, y2),
        WHITE,
        1
    )

    font = cv2.FONT_HERSHEY_SIMPLEX

    font_scale = 0.62

    thickness = 2

    (
        text_width,
        text_height
    ), baseline = cv2.getTextSize(
        text,
        font,
        font_scale,
        thickness
    )

    text_x = (
        x1
        +
        (
            (x2 - x1 - text_width)
            //
            2
        )
    )

    text_y = (
        y1
        +
        (
            (y2 - y1 + text_height)
            //
            2
        )
    )

    cv2.putText(
        frame,
        text,
        (
            text_x,
            text_y
        ),
        font,
        font_scale,
        WHITE,
        thickness,
        cv2.LINE_AA
    )


# ============================================================
# DRAW INFORMATION PANEL
# ============================================================

def draw_information_panel(
    frame,
    student
):

    height, width = frame.shape[:2]

    panel_height = 78

    overlay = frame.copy()

    cv2.rectangle(
        overlay,
        (
            0,
            0
        ),
        (
            width,
            panel_height
        ),
        BG_COLOR,
        -1
    )

    cv2.addWeighted(
        overlay,
        0.88,
        frame,
        0.12,
        0,
        frame
    )

    student_name = str(
        student[2]
    )

    school_id = str(
        student[1]
    )

    course = str(
        student[3]
    )

    year = str(
        student[4]
    )

    section = str(
        student[5]
    )

    cv2.putText(
        frame,
        "ATTENDX FACE REGISTRATION",
        (18, 27),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.67,
        WHITE,
        2,
        cv2.LINE_AA
    )

    details = (
        student_name
        + "  |  "
        + school_id
        + "  |  "
        + course
        + " "
        + year
        + "-"
        + section
    )

    cv2.putText(
        frame,
        details,
        (18, 57),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.48,
        LIGHT_GRAY,
        1,
        cv2.LINE_AA
    )


# ============================================================
# DRAW BOTTOM CONTROLS
# ============================================================

def draw_bottom_controls(
    frame,
    register_enabled
):

    height, width = frame.shape[:2]

    panel_top = height - 100

    overlay = frame.copy()

    cv2.rectangle(
        overlay,
        (
            0,
            panel_top
        ),
        (
            width,
            height
        ),
        BG_COLOR,
        -1
    )

    cv2.addWeighted(
        overlay,
        0.94,
        frame,
        0.06,
        0,
        frame
    )

    button_margin = 18

    button_gap = 14

    button_width = (
        width
        -
        (
            button_margin * 2
        )
        -
        button_gap
    ) // 2

    button_y1 = (
        panel_top + 18
    )

    button_y2 = (
        height - 18
    )

    register_button = (
        button_margin,
        button_y1,
        button_margin + button_width,
        button_y2
    )

    cancel_x1 = (
        button_margin
        +
        button_width
        +
        button_gap
    )

    cancel_button = (
        cancel_x1,
        button_y1,
        width - button_margin,
        button_y2
    )

    draw_button(
        frame,
        register_button,
        "REGISTER FACE",
        register_enabled
    )

    draw_button(
        frame,
        cancel_button,
        "CANCEL",
        True
    )

    return (
        register_button,
        cancel_button
    )


# ============================================================
# DRAW STATUS
# ============================================================

def draw_status(
    frame
):

    height, width = frame.shape[:2]

    if status_type == "success":

        color = GREEN

    elif status_type == "error":

        color = RED

    elif status_type == "warning":

        color = YELLOW

    else:

        color = WHITE

    text = str(
        last_status
    )

    font = cv2.FONT_HERSHEY_SIMPLEX

    scale = 0.58

    thickness = 2

    (
        text_width,
        text_height
    ), baseline = cv2.getTextSize(
        text,
        font,
        scale,
        thickness
    )

    x = (
        width - text_width
    ) // 2

    y = height - 116

    cv2.putText(
        frame,
        text,
        (
            x,
            y
        ),
        font,
        scale,
        color,
        thickness,
        cv2.LINE_AA
    )


# ============================================================
# CREATE REGISTRATION WINDOW
# ============================================================

def setup_window():

    cv2.namedWindow(
        WINDOW_NAME,
        cv2.WINDOW_NORMAL
    )

    cv2.resizeWindow(
        WINDOW_NAME,
        WINDOW_WIDTH,
        WINDOW_HEIGHT
    )


# ============================================================
# REGISTER STUDENT FACE
# ============================================================

def register_student_face(
    student_id
):

    global register_clicked
    global cancel_clicked

    global last_detection
    global last_detection_frame

    global current_detection_width
    global current_detection_interval
    global performance_mode

    global fps_value

    # --------------------------------------------------------
    # Reset states
    # --------------------------------------------------------

    with ui_lock:

        register_clicked = False
        cancel_clicked = False

    last_detection = []

    last_detection_frame = -1

    current_detection_width = (
        NORMAL_DETECTION_WIDTH
    )

    current_detection_interval = (
        NORMAL_DETECTION_INTERVAL
    )

    performance_mode = "NORMAL"

    fps_value = 0.0

    set_status(
        "LOOK AT THE CAMERA",
        "normal"
    )

    # --------------------------------------------------------
    # Get student
    # --------------------------------------------------------

    student = get_student(
        student_id
    )

    if student is None:

        print(
            "Student not found."
        )

        return False

    # --------------------------------------------------------
    # Console information
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Create camera
    # --------------------------------------------------------

    camera = create_camera()

    if camera is None:

        print(
            "Camera: NOT AVAILABLE"
        )

        return False

    print(
        "Camera: READY"
    )

    print(
        "Camera preview:",
        str(CAMERA_WIDTH)
        + "x"
        + str(CAMERA_HEIGHT)
    )

    print(
        "Use the REGISTER FACE button to capture."
    )

    print(
        "Use the CANCEL button to exit."
    )

    print()

    # --------------------------------------------------------
    # Setup window
    # --------------------------------------------------------

    setup_window()

    # --------------------------------------------------------
    # Mouse callback
    # --------------------------------------------------------

    callback_data = {
        "register_button": (
            18,
            0,
            0,
            0
        ),
        "cancel_button": (
            18,
            0,
            0,
            0
        )
    }

    cv2.setMouseCallback(
        WINDOW_NAME,
        register_button_callback,
        callback_data
    )

    # --------------------------------------------------------
    # Performance controller
    # --------------------------------------------------------

    performance = AdaptivePerformance()

    # --------------------------------------------------------
    # FPS variables
    # --------------------------------------------------------

    fps_counter = 0

    fps_start = time.perf_counter()

    frame_number = 0

    # --------------------------------------------------------
    # Main camera loop
    # --------------------------------------------------------

    try:

        while True:

            # =================================================
            # READ CAMERA
            # =================================================

            success, frame = (
                camera.read()
            )

            if not success:

                set_status(
                    "CAMERA READ ERROR",
                    "error"
                )

                print(
                    "Failed to read camera."
                )

                break

            # ------------------------------------------------
            # Ensure frame is usable.
            # ------------------------------------------------

            if frame is None:
                continue

            if frame.size == 0:
                continue

            frame_number += 1

            # =================================================
            # FPS CALCULATION
            # =================================================

            fps_counter += 1

            current_time = (
                time.perf_counter()
            )

            elapsed = (
                current_time
                -
                fps_start
            )

            if elapsed >= 1.0:

                fps_value = (
                    fps_counter
                    /
                    elapsed
                )

                performance.update(
                    fps_value
                )

                fps_counter = 0

                fps_start = (
                    current_time
                )

            # =================================================
            # FACE DETECTION
            # =================================================

            if (
                last_detection_frame < 0
                or
                (
                    frame_number
                    -
                    last_detection_frame
                )
                >= current_detection_interval
            ):

                try:

                    detected_faces = (
                        detect_faces(
                            frame
                        )
                    )

                    last_detection = (
                        detected_faces
                    )

                    last_detection_frame = (
                        frame_number
                    )

                except Exception as error:

                    print(
                        "Face detection error:",
                        error
                    )

                    last_detection = []

                    last_detection_frame = (
                        frame_number
                    )

            # =================================================
            # DRAW INFORMATION
            # =================================================

            display_frame = (
                frame.copy()
            )

            draw_information_panel(
                display_frame,
                student
            )

            # =================================================
            # FACE STATE
            # =================================================

            face_ready = False

            selected_face = None

            if len(last_detection) == 1:

                selected_face = (
                    last_detection[0]
                )

                validation = (
                    validate_face_position(
                        frame,
                        selected_face
                    )
                )

                if validation["valid"]:

                    face_ready = True

                    draw_face_box(
                        display_frame,
                        selected_face,
                        True
                    )

                    set_status(
                        "FACE READY - CLICK REGISTER FACE",
                        "success"
                    )

                else:

                    draw_face_box(
                        display_frame,
                        selected_face,
                        False
                    )

                    set_status(
                        validation["reason"],
                        "warning"
                    )

            elif len(last_detection) > 1:

                for location in last_detection:

                    draw_face_box(
                        display_frame,
                        location,
                        False
                    )

                set_status(
                    "ONLY ONE FACE ALLOWED",
                    "error"
                )

            else:

                set_status(
                    "NO FACE DETECTED",
                    "warning"
                )

            # =================================================
            # TOP RIGHT PERFORMANCE INFO
            # =================================================

            performance_text = (
                "FPS "
                + str(
                    int(fps_value)
                )
                + "  |  "
                + performance_mode
            )

            cv2.putText(
                display_frame,
                performance_text,
                (
                    display_frame.shape[1] - 185,
                    28
                ),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                LIGHT_GRAY,
                1,
                cv2.LINE_AA
            )

            # =================================================
            # STATUS
            # =================================================

            draw_status(
                display_frame
            )

            # =================================================
            # BUTTONS
            # =================================================

            (
                register_button,
                cancel_button
            ) = draw_bottom_controls(
                display_frame,
                face_ready
            )

            callback_data[
                "register_button"
            ] = register_button

            callback_data[
                "cancel_button"
            ] = cancel_button

            # =================================================
            # SHOW FRAME
            # =================================================

            cv2.imshow(
                WINDOW_NAME,
                display_frame
            )

            # =================================================
            # GET BUTTON STATE
            # =================================================

            with ui_lock:

                do_register = (
                    register_clicked
                )

                do_cancel = (
                    cancel_clicked
                )

                register_clicked = False

                cancel_clicked = False

            # =================================================
            # CANCEL
            # =================================================

            if do_cancel:

                print(
                    "Face registration cancelled."
                )

                set_status(
                    "CANCELLED",
                    "error"
                )

                break

            # =================================================
            # REGISTER
            # =================================================

            if do_register:

                # --------------------------------------------
                # Must have exactly one detected face.
                # --------------------------------------------

                if len(last_detection) != 1:

                    set_status(
                        "ONE FACE IS REQUIRED",
                        "error"
                    )

                    continue

                # --------------------------------------------
                # IMPORTANT FIX
                #
                # Do NOT call face_locations() again here.
                #
                # The previous version performed a second HOG
                # detection on the original frame. That could
                # produce:
                #
                # FACE READY
                #       ↓
                # REGISTER FACE
                #       ↓
                # FACE NOT FOUND
                #
                # We now use the face that was already detected.
                # --------------------------------------------

                capture_frame = (
                    frame.copy()
                )

                capture_location = (
                    last_detection[0]
                )

                # --------------------------------------------
                # Validate the already detected face.
                # --------------------------------------------

                current_validation = (
                    validate_face_position(
                        capture_frame,
                        capture_location
                    )
                )

                if not current_validation["valid"]:

                    set_status(
                        current_validation["reason"],
                        "warning"
                    )

                    continue

                # --------------------------------------------
                # Make sure the detected face coordinates
                # are inside the original frame.
                # --------------------------------------------

                frame_height, frame_width = (
                    capture_frame.shape[:2]
                )

                top, right, bottom, left = (
                    capture_location
                )

                top = max(
                    0,
                    min(
                        top,
                        frame_height - 1
                    )
                )

                right = max(
                    1,
                    min(
                        right,
                        frame_width
                    )
                )

                bottom = max(
                    1,
                    min(
                        bottom,
                        frame_height
                    )
                )

                left = max(
                    0,
                    min(
                        left,
                        frame_width - 1
                    )
                )

                capture_location = (
                    top,
                    right,
                    bottom,
                    left
                )

                # --------------------------------------------
                # Make RGB version of the ORIGINAL clear frame.
                # --------------------------------------------

                try:

                    capture_rgb = cv2.cvtColor(
                        capture_frame,
                        cv2.COLOR_BGR2RGB
                    )

                except Exception as error:

                    print(
                        "Capture conversion error:",
                        error
                    )

                    set_status(
                        "CAPTURE FAILED",
                        "error"
                    )

                    continue

                set_status(
                    "CAPTURING FACE...",
                    "normal"
                )

                # --------------------------------------------
                # FACE ENCODING
                #
                # We use the already detected face location.
                #
                # No second face_locations() call.
                # --------------------------------------------

                try:

                    capture_encoding_list = (
                        face_recognition.face_encodings(
                            capture_rgb,
                            [capture_location],
                            num_jitters=ENCODING_JITTERS
                        )
                    )

                except Exception as error:

                    print(
                        "Face encoding error:",
                        error
                    )

                    set_status(
                        "FACE ENCODING FAILED",
                        "error"
                    )

                    continue

                # --------------------------------------------
                # Verify encoding
                # --------------------------------------------

                if (
                    not capture_encoding_list
                    or
                    len(capture_encoding_list) != 1
                ):

                    set_status(
                        "FACE ENCODING FAILED",
                        "error"
                    )

                    continue

                captured_encoding = (
                    capture_encoding_list[0]
                )

                # --------------------------------------------
                # Check encoding shape.
                # --------------------------------------------

                if (
                    captured_encoding is None
                    or
                    len(captured_encoding) != 128
                ):

                    set_status(
                        "INVALID FACE DATA",
                        "error"
                    )

                    continue

                # =================================================
                # DUPLICATE CHECK
                # =================================================

                set_status(
                    "CHECKING REGISTERED FACES...",
                    "normal"
                )

                print()
                print(
                    "Checking face..."
                )

                try:

                    duplicate_result = (
                        check_duplicate_face(
                            student_id,
                            captured_encoding
                        )
                    )

                except Exception as error:

                    print(
                        "Duplicate check error:",
                        error
                    )

                    set_status(
                        "DUPLICATE CHECK FAILED",
                        "error"
                    )

                    continue

                if duplicate_result[
                    "duplicate"
                ]:

                    duplicate_student_id = (
                        duplicate_result[
                            "student_id"
                        ]
                    )

                    distance = (
                        duplicate_result[
                            "distance"
                        ]
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
                        round(
                            distance,
                            6
                        )
                    )

                    print(
                        "Duplicate tolerance:",
                        DUPLICATE_TOLERANCE
                    )

                    print()

                    set_status(
                        "FACE ALREADY REGISTERED",
                        "error"
                    )

                    continue

                # =================================================
                # PREPARE FACE DATA
                # =================================================

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

                # =================================================
                # SAVE
                # =================================================

                set_status(
                    "SAVING FACE DATA...",
                    "normal"
                )

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

                    set_status(
                        "SAVE FAILED",
                        "error"
                    )

                    continue

                # =================================================
                # SUCCESS
                # =================================================

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

                set_status(
                    "FACE REGISTERED SUCCESSFULLY",
                    "success"
                )

                # Give OpenCV enough time
                # to display the success frame.
                cv2.imshow(
                    WINDOW_NAME,
                    display_frame
                )

                cv2.waitKey(
                    500
                )

                return True

            # =================================================
            # WINDOW CLOSE DETECTION
            # =================================================

            try:

                window_visible = (
                    cv2.getWindowProperty(
                        WINDOW_NAME,
                        cv2.WND_PROP_VISIBLE
                    )
                )

                if window_visible < 1:

                    print(
                        "Registration window closed."
                    )

                    break

            except Exception:

                pass

            # ------------------------------------------------
            # Keep UI responsive.
            # ------------------------------------------------

            cv2.waitKey(1)

    finally:

        # =====================================================
        # CLEANUP
        # =====================================================

        try:

            camera.release()

        except Exception:

            pass

        try:

            cv2.destroyWindow(
                WINDOW_NAME
            )

        except Exception:

            pass

        cv2.waitKey(1)

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

    result = register_student_face(
        student_id
    )

    if result:

        print(
            "Registration completed."
        )

    else:

        print(
            "Registration was not completed."
        )

# ============================================================
# ATTENDX GUIDED AUTOMATIC FACE REGISTRATION
# ============================================================

def register_student_face(student_id):
    """
    Guided automatic registration:

    camera -> face detection -> position -> size -> quality ->
    stable hold -> 3/2/1 countdown -> automatic capture ->
    validation -> encoding -> duplicate check -> save.
    """
    import cv2
    import time
    import face_recognition
    import numpy as np

    from face_system import save_face_template

    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT id, school_id, name, course, year, section
            FROM students
            WHERE id = ?
        """, (student_id,))
        student = cursor.fetchone()
    finally:
        connection.close()

    if not student:
        print("Student not found.")
        return False

    camera = cv2.VideoCapture(0)
    if not camera.isOpened():
        print("Camera: NOT AVAILABLE")
        return False

    window_name = "AttendX | Guided Face Registration"
    cv2.namedWindow(window_name)

    stable_frames = 0
    required_stable_frames = 18
    countdown_started = None
    countdown_value = None
    captured = False
    result_message = "POSITION YOUR FACE INSIDE THE GUIDE"
    result_color = (255, 200, 0)

    try:
        while True:
            ok, frame = camera.read()
            if not ok or frame is None:
                result_message = "CAMERA READ ERROR"
                result_color = (0, 0, 255)
                break

            frame = cv2.flip(frame, 1)
            height, width = frame.shape[:2]
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            locations = face_recognition.face_locations(
                rgb, model="hog"
            )

            ready = False

            if len(locations) == 0:
                stable_frames = 0
                countdown_started = None
                countdown_value = None
                result_message = "LOOK AT THE CAMERA"
                result_color = (0, 165, 255)

            elif len(locations) > 1:
                stable_frames = 0
                countdown_started = None
                countdown_value = None
                result_message = "ONLY ONE FACE ALLOWED"
                result_color = (0, 0, 255)

            else:
                top, right, bottom, left = locations[0]
                face_width = right - left
                face_height = bottom - top
                center_x = (left + right) // 2
                center_y = (top + bottom) // 2

                guide_left = int(width * 0.28)
                guide_right = int(width * 0.72)
                guide_top = int(height * 0.18)
                guide_bottom = int(height * 0.82)

                inside = (
                    guide_left <= center_x <= guide_right
                    and guide_top <= center_y <= guide_bottom
                )

                size_ok = (
                    face_width >= 100
                    and face_height >= 100
                    and face_width <= int(width * 0.75)
                    and face_height <= int(height * 0.75)
                )

                face_crop = frame[
                    max(0, top):min(height, bottom),
                    max(0, left):min(width, right)
                ]

                quality_ok = False
                if face_crop.size > 0:
                    gray = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)
                    quality_score = float(cv2.Laplacian(
                        gray, cv2.CV_64F
                    ).var())
                    quality_ok = quality_score >= 35.0
                else:
                    quality_score = 0.0

                cv2.rectangle(
                    frame,
                    (left, top),
                    (right, bottom),
                    (0, 255, 0) if inside and size_ok and quality_ok
                    else (0, 0, 255),
                    2
                )

                if not inside:
                    stable_frames = 0
                    countdown_started = None
                    countdown_value = None
                    result_message = "MOVE YOUR FACE TO THE CENTER"
                    result_color = (0, 165, 255)

                elif not size_ok:
                    stable_frames = 0
                    countdown_started = None
                    countdown_value = None
                    result_message = "MOVE CLOSER / FARTHER"
                    result_color = (0, 165, 255)

                elif not quality_ok:
                    stable_frames = 0
                    countdown_started = None
                    countdown_value = None
                    result_message = "IMPROVE LIGHTING / HOLD STILL"
                    result_color = (0, 165, 255)

                else:
                    stable_frames += 1
                    ready = stable_frames >= required_stable_frames
                    result_message = "HOLD STILL — FACE READY"
                    result_color = (0, 255, 0)

                    if ready and countdown_started is None:
                        countdown_started = time.time()

                    if countdown_started is not None:
                        elapsed = time.time() - countdown_started
                        countdown_value = 3 - int(elapsed)

                        if countdown_value > 0:
                            result_message = (
                                "CAPTURING IN "
                                + str(countdown_value)
                            )
                            result_color = (0, 255, 0)
                        else:
                            encodings = face_recognition.face_encodings(
                                rgb, [locations[0]]
                            )

                            if len(encodings) != 1:
                                result_message = "NOT VERIFIED — ENCODING FAILED"
                                result_color = (0, 0, 255)
                                countdown_started = None
                                stable_frames = 0
                                continue

                            encoding = np.asarray(
                                encodings[0],
                                dtype=np.float64
                            )

                            if encoding.shape != (128,):
                                result_message = "NOT VERIFIED — INVALID ENCODING"
                                result_color = (0, 0, 255)
                                countdown_started = None
                                stable_frames = 0
                                continue

                            duplicate = check_duplicate_face(
                                student_id,
                                encoding
                            )

                            if duplicate.get("duplicate"):
                                result_message = (
                                    "FACE ALREADY REGISTERED TO ANOTHER STUDENT"
                                )
                                result_color = (0, 0, 255)
                                print(duplicate.get("message", result_message))
                                break

                            saved = save_face_template(
                                student_id,
                                encoding
                            )

                            if saved.get("success"):
                                captured = True
                                result_message = "FACE REGISTRATION COMPLETE"
                                result_color = (0, 255, 0)
                            else:
                                result_message = (
                                    "FACE SAVE FAILED: "
                                    + str(saved.get("message", "Unknown error"))
                                )
                                result_color = (0, 0, 255)

                            break

            cv2.rectangle(
                frame,
                (int(width * 0.28), int(height * 0.18)),
                (int(width * 0.72), int(height * 0.82)),
                result_color,
                2
            )

            cv2.putText(
                frame,
                "ATTENDX GUIDED FACE REGISTRATION",
                (20, 34),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.72,
                (255, 255, 255),
                2
            )

            cv2.putText(
                frame,
                result_message,
                (20, 68),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.62,
                result_color,
                2
            )

            cv2.putText(
                frame,
                "Student: " + str(student[2]),
                (20, 100),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (255, 255, 255),
                2
            )

            cv2.putText(
                frame,
                "ESC / Q = CANCEL",
                (20, height - 22),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.52,
                (220, 220, 220),
                1
            )

            cv2.imshow(window_name, frame)

            key = cv2.waitKey(1) & 0xFF
            if key in (27, ord("q")):
                break

    finally:
        camera.release()
        cv2.destroyAllWindows()

    return captured