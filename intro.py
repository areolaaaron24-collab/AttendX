
import os
import tkinter as tk
import time
import math

from PIL import Image, ImageTk, ImageFilter, ImageDraw, ImageFont


# ============================================================
# ATTENDX INTRO
# ============================================================

BASE_DIR = r"C:\SchoolAttendanceSystem"

LOGO_PATH = os.path.join(
    BASE_DIR,
    "assets",
    "AttendX_Logo.png"
)

WINDOW_W = 1408
WINDOW_H = 768

FPS = 60


# ============================================================
# COLORS
# ============================================================

BACKGROUND = (3, 5, 14)

TEXT_MAIN = (245, 245, 255)

TEXT_SECONDARY = (185, 188, 220)

GLOW_COLOR = (105, 95, 220)


# ============================================================
# ANIMATION SETTINGS
# ============================================================

INITIALIZING_TIME = 4.0

SYSTEM_TIME = 1.5

WELCOME_TIME = 1.5

LOGO_TIME = 3.5

LOGO_HOLD_TIME = 1.0

DOT_SPEED = 0.32

DOT_CYCLES = 2


# ============================================================
# HELPERS
# ============================================================

def clamp(value, minimum=0.0, maximum=1.0):
    return max(
        minimum,
        min(maximum, value)
    )


def ease_out(value):
    value = clamp(value)

    return 1 - pow(
        1 - value,
        3
    )


def ease_in_out(value):
    value = clamp(value)

    return value * value * (
        3 - 2 * value
    )


def create_background(width, height):
    return Image.new(
        "RGBA",
        (width, height),
        (
            BACKGROUND[0],
            BACKGROUND[1],
            BACKGROUND[2],
            255
        )
    )


def create_soft_light(
    width,
    height,
    strength=1.0
):

    light = Image.new(
        "RGBA",
        (width, height),
        (0, 0, 0, 0)
    )

    center_x = width // 2

    center_y = height // 2

    glow_size = int(
        min(width, height) * 0.72
    )

    glow = Image.new(
        "RGBA",
        (glow_size, glow_size),
        (0, 0, 0, 0)
    )

    pixels = glow.load()

    cx = glow_size / 2

    cy = glow_size / 2

    radius = glow_size / 2

    for y in range(glow_size):

        for x in range(glow_size):

            dx = x - cx

            dy = y - cy

            distance = math.sqrt(
                dx * dx +
                dy * dy
            )

            if distance < radius:

                factor = 1 - (
                    distance / radius
                )

                factor = factor * factor

                alpha = int(
                    30 *
                    factor *
                    strength
                )

                pixels[x, y] = (
                    80,
                    70,
                    160,
                    alpha
                )

    light.alpha_composite(
        glow,
        (
            center_x - glow_size // 2,
            center_y - glow_size // 2
        )
    )

    return light


# ============================================================
# ATTENDX INTRO CLASS
# ============================================================

class AttendXIntro:

    def __init__(self, root):

        self.root = root

        self.root.overrideredirect(True)

        self.root.configure(
            bg="#03050E"
        )

        screen_w = (
            self.root.winfo_screenwidth()
        )

        screen_h = (
            self.root.winfo_screenheight()
        )

        x = (
            screen_w - WINDOW_W
        ) // 2

        y = (
            screen_h - WINDOW_H
        ) // 2

        self.root.geometry(
            f"{WINDOW_W}x{WINDOW_H}+{x}+{y}"
        )

        self.canvas = tk.Canvas(
            self.root,
            width=WINDOW_W,
            height=WINDOW_H,
            bg="#03050E",
            highlightthickness=0
        )

        self.canvas.pack()

        # ----------------------------------------------------
        # CHECK LOGO
        # ----------------------------------------------------

        if not os.path.exists(LOGO_PATH):

            self.show_error(
                "AttendX logo was not found.\n\n"
                f"{LOGO_PATH}"
            )

            return

        # ----------------------------------------------------
        # LOAD LOGO
        # ----------------------------------------------------

        try:

            self.original_logo = (
                Image.open(
                    LOGO_PATH
                ).convert("RGBA")
            )

        except Exception as error:

            self.show_error(
                "Unable to load AttendX logo.\n\n"
                f"{error}"
            )

            return

        # ----------------------------------------------------
        # PREPARE LOGO
        # ----------------------------------------------------

        max_logo_width = 560

        max_logo_height = 330

        logo_w, logo_h = (
            self.original_logo.size
        )

        scale = min(
            max_logo_width / logo_w,
            max_logo_height / logo_h
        )

        self.logo_w = int(
            logo_w * scale
        )

        self.logo_h = int(
            logo_h * scale
        )

        self.logo_base = (
            self.original_logo.resize(
                (
                    self.logo_w,
                    self.logo_h
                ),
                Image.Resampling.LANCZOS
            )
        )

        # ----------------------------------------------------
        # BACKGROUND
        # ----------------------------------------------------

        self.background = (
            create_background(
                WINDOW_W,
                WINDOW_H
            )
        )

        self.soft_light = (
            create_soft_light(
                WINDOW_W,
                WINDOW_H
            )
        )

        # ----------------------------------------------------
        # ANIMATION STATE
        # ----------------------------------------------------

        self.start_time = (
            time.perf_counter()
        )

        self.finished = False

        self.current_frame = (
            self.background.copy()
        )

        # ----------------------------------------------------
        # START
        # ----------------------------------------------------

        self.root.after(
            20,
            self.animate
        )

    # ========================================================
    # ERROR
    # ========================================================

    def show_error(self, message):

        self.canvas.delete(
            "all"
        )

        self.canvas.create_text(
            WINDOW_W // 2,
            WINDOW_H // 2,
            text=message,
            fill="#FFFFFF",
            font=(
                "Segoe UI",
                18
            ),
            justify="center"
        )

        self.root.after(
            4000,
            self.root.destroy
        )

    # ========================================================
    # FONT
    # ========================================================

    def get_font(
        self,
        size,
        bold=True
    ):

        if bold:

            font_paths = [
                r"C:\Windows\Fonts\segoeuib.ttf",
                r"C:\Windows\Fonts\arialbd.ttf"
            ]

        else:

            font_paths = [
                r"C:\Windows\Fonts\segoeui.ttf",
                r"C:\Windows\Fonts\arial.ttf"
            ]

        for path in font_paths:

            if os.path.exists(path):

                try:

                    return ImageFont.truetype(
                        path,
                        size
                    )

                except Exception:

                    pass

        return ImageFont.load_default()

    # ========================================================
    # CENTER TEXT
    # ========================================================

    def draw_center_text(
        self,
        text,
        y,
        size,
        alpha,
        bold=True,
        color=TEXT_MAIN
    ):

        if alpha <= 0:

            return

        alpha = clamp(
            alpha
        )

        layer = Image.new(
            "RGBA",
            (
                WINDOW_W,
                WINDOW_H
            ),
            (0, 0, 0, 0)
        )

        font = self.get_font(
            size,
            bold
        )

        draw = ImageDraw.Draw(
            layer
        )

        bbox = draw.textbbox(
            (0, 0),
            text,
            font=font
        )

        text_width = (
            bbox[2] - bbox[0]
        )

        text_height = (
            bbox[3] - bbox[1]
        )

        text_x = (
            WINDOW_W -
            text_width
        ) // 2

        text_y = int(
            y -
            text_height / 2
        )

        final_alpha = int(
            255 *
            alpha
        )

        # ----------------------------------------------------
        # TEXT GLOW
        # ----------------------------------------------------

        if alpha > 0.08:

            glow_layer = Image.new(
                "RGBA",
                (
                    WINDOW_W,
                    WINDOW_H
                ),
                (0, 0, 0, 0)
            )

            glow_draw = ImageDraw.Draw(
                glow_layer
            )

            glow_draw.text(
                (
                    text_x,
                    text_y
                ),
                text,
                font=font,
                fill=(
                    GLOW_COLOR[0],
                    GLOW_COLOR[1],
                    GLOW_COLOR[2],
                    int(
                        42 *
                        alpha
                    )
                )
            )

            glow_layer = (
                glow_layer.filter(
                    ImageFilter.GaussianBlur(
                        10
                    )
                )
            )

            layer.alpha_composite(
                glow_layer
            )

        # ----------------------------------------------------
        # MAIN TEXT
        # ----------------------------------------------------

        draw = ImageDraw.Draw(
            layer
        )

        draw.text(
            (
                text_x,
                text_y
            ),
            text,
            font=font,
            fill=(
                color[0],
                color[1],
                color[2],
                final_alpha
            )
        )

        self.current_frame.alpha_composite(
            layer
        )

    # ========================================================
    # INITIALIZING TEXT
    # ========================================================

    def draw_initializing(
        self,
        elapsed
    ):

        base_text = (
            "INITIALIZING ATTENDX"
        )

        # ----------------------------------------------------
        # TYPING EFFECT
        # ----------------------------------------------------

        typing_duration = 1.45

        typing_progress = clamp(
            elapsed /
            typing_duration
        )

        characters = int(
            len(base_text) *
            typing_progress
        )

        visible_text = (
            base_text[
                :characters
            ]
        )

        # ----------------------------------------------------
        # DOT ANIMATION
        #
        # .
        # ..
        # ...
        #
        # REPEATS EXACTLY 2 TIMES
        # ----------------------------------------------------

        full_dot_cycle = (
            DOT_SPEED * 3
        )

        total_dot_time = (
            full_dot_cycle *
            DOT_CYCLES
        )

        if elapsed < total_dot_time:

            dot_step = int(
                elapsed /
                DOT_SPEED
            ) % 3

            dots = "." * (
                dot_step + 1
            )

        else:

            dots = "..."

        # ----------------------------------------------------
        # BUILD TEXT
        # ----------------------------------------------------

        text = visible_text

        if len(visible_text) == len(
            base_text
        ):

            text += dots

        # ----------------------------------------------------
        # FADE IN
        # ----------------------------------------------------

        fade = ease_out(
            clamp(
                elapsed /
                0.45
            )
        )

        # ----------------------------------------------------
        # SLIGHT MOVEMENT
        # ----------------------------------------------------

        movement = int(
            8 *
            (
                1 -
                ease_out(
                    clamp(
                        elapsed /
                        0.8
                    )
                )
            )
        )

        center_y = (
            WINDOW_H // 2 +
            movement
        )

        self.draw_center_text(
            text,
            center_y,
            34,
            fade,
            bold=True,
            color=(
                235,
                236,
                255
            )
        )

        # ----------------------------------------------------
        # LOADING LINE
        # ----------------------------------------------------

        line_progress = ease_out(
            clamp(
                (elapsed - 0.25) /
                3.0
            )
        )

        if line_progress > 0:

            line_width = int(
                220 *
                line_progress
            )

            line_y = (
                WINDOW_H // 2 +
                48
            )

            draw = ImageDraw.Draw(
                self.current_frame
            )

            # Background line

            draw.rounded_rectangle(
                (
                    WINDOW_W // 2 - 110,
                    line_y,
                    WINDOW_W // 2 + 110,
                    line_y + 2
                ),
                radius=2,
                fill=(
                    50,
                    50,
                    75,
                    80
                )
            )

            # Progress line

            draw.rounded_rectangle(
                (
                    WINDOW_W // 2 -
                    line_width // 2,

                    line_y,

                    WINDOW_W // 2 +
                    line_width // 2,

                    line_y + 2
                ),
                radius=2,
                fill=(
                    120,
                    105,
                    230,
                    int(
                        130 *
                        fade
                    )
                )
            )

    # ========================================================
    # SMART ATTENDANCE SYSTEM
    # ========================================================

    def draw_system_text(
        self,
        elapsed
    ):

        fade_in = ease_out(
            clamp(
                elapsed /
                0.65
            )
        )

        fade_out = 1.0

        if elapsed > 1.0:

            fade_out = 1 - clamp(
                (
                    elapsed - 1.0
                ) /
                0.5
            )

        alpha = (
            fade_in *
            fade_out
        )

        movement = int(
            10 *
            (
                1 -
                ease_out(
                    clamp(
                        elapsed /
                        0.7
                    )
                )
            )
        )

        self.draw_center_text(
            "SMART ATTENDANCE SYSTEM",
            WINDOW_H // 2 +
            movement,
            28,
            alpha,
            bold=False,
            color=TEXT_SECONDARY
        )

    # ========================================================
    # WELCOME
    # ========================================================

    def draw_welcome(
        self,
        elapsed
    ):

        fade_in = ease_out(
            clamp(
                elapsed /
                0.65
            )
        )

        fade_out = 1.0

        if elapsed > 1.0:

            fade_out = 1 - clamp(
                (
                    elapsed - 1.0
                ) /
                0.5
            )

        alpha = (
            fade_in *
            fade_out
        )

        scale_progress = ease_out(
            clamp(
                elapsed /
                0.8
            )
        )

        size = int(
            52 +
            7 *
            scale_progress
        )

        movement = int(
            12 *
            (
                1 -
                ease_out(
                    clamp(
                        elapsed /
                        0.8
                    )
                )
            )
        )

        self.draw_center_text(
            "WELCOME",
            WINDOW_H // 2 +
            movement,
            size,
            alpha,
            bold=True,
            color=(
                250,
                250,
                255
            )
        )

    # ========================================================
    # LOGO
    # ========================================================

    def draw_logo(
        self,
        elapsed
    ):

        # ----------------------------------------------------
        # FADE
        # ----------------------------------------------------

        fade_progress = ease_in_out(
            clamp(
                elapsed /
                1.25
            )
        )

        # ----------------------------------------------------
        # ZOOM
        # ----------------------------------------------------

        zoom_progress = ease_out(
            clamp(
                elapsed /
                1.35
            )
        )

        scale = (
            0.84 +
            0.16 *
            zoom_progress
        )

        logo_w = int(
            self.logo_w *
            scale
        )

        logo_h = int(
            self.logo_h *
            scale
        )

        logo = (
            self.logo_base.resize(
                (
                    logo_w,
                    logo_h
                ),
                Image.Resampling.LANCZOS
            )
        )

        # ----------------------------------------------------
        # LOGO ALPHA
        # ----------------------------------------------------

        alpha = int(
            255 *
            fade_progress
        )

        logo_alpha = (
            logo.getchannel(
                "A"
            )
        )

        logo_alpha = (
            logo_alpha.point(
                lambda p:
                int(
                    p *
                    alpha /
                    255
                )
            )
        )

        logo.putalpha(
            logo_alpha
        )

        # ----------------------------------------------------
        # LOGO GLOW
        # ----------------------------------------------------

        if fade_progress > 0.04:

            glow = logo.copy()

            glow_alpha = (
                glow.getchannel(
                    "A"
                )
            )

            glow_alpha = (
                glow_alpha.filter(
                    ImageFilter.GaussianBlur(
                        15
                    )
                )
            )

            glow_alpha = (
                glow_alpha.point(
                    lambda p:
                    int(
                        p *
                        0.25
                    )
                )
            )

            glow.putalpha(
                glow_alpha
            )

            glow_layer = Image.new(
                "RGBA",
                (
                    WINDOW_W,
                    WINDOW_H
                ),
                (0, 0, 0, 0)
            )

            glow_x = (
                WINDOW_W -
                logo_w
            ) // 2

            glow_y = (
                WINDOW_H -
                logo_h
            ) // 2 - 8

            glow_layer.alpha_composite(
                glow,
                (
                    glow_x,
                    glow_y
                )
            )

            self.current_frame.alpha_composite(
                glow_layer
            )

        # ----------------------------------------------------
        # LOGO MOVEMENT
        # ----------------------------------------------------

        slide_progress = ease_out(
            clamp(
                elapsed /
                1.25
            )
        )

        slide = int(
            24 *
            (
                1 -
                slide_progress
            )
        )

        logo_x = (
            WINDOW_W -
            logo_w
        ) // 2

        logo_y = (
            WINDOW_H -
            logo_h
        ) // 2 - 8 + slide

        # ----------------------------------------------------
        # DRAW LOGO
        # ----------------------------------------------------

        self.current_frame.alpha_composite(
            logo,
            (
                logo_x,
                logo_y
            )
        )

    # ========================================================
    # MAIN ANIMATION
    # ========================================================

    def animate(self):

        if self.finished:

            return

        current_time = (
            time.perf_counter()
        )

        elapsed = (
            current_time -
            self.start_time
        )

        # ====================================================
        # PHASE 1
        # INITIALIZING
        # ====================================================

        if elapsed < INITIALIZING_TIME:

            self.current_frame = (
                self.background.copy()
            )

            self.current_frame.alpha_composite(
                self.soft_light
            )

            self.draw_initializing(
                elapsed
            )

        # ====================================================
        # PHASE 2
        # SMART ATTENDANCE SYSTEM
        # ====================================================

        elif elapsed < (
            INITIALIZING_TIME +
            SYSTEM_TIME
        ):

            phase_elapsed = (
                elapsed -
                INITIALIZING_TIME
            )

            self.current_frame = (
                self.background.copy()
            )

            self.current_frame.alpha_composite(
                self.soft_light
            )

            self.draw_system_text(
                phase_elapsed
            )

        # ====================================================
        # PHASE 3
        # WELCOME
        # ====================================================

        elif elapsed < (
            INITIALIZING_TIME +
            SYSTEM_TIME +
            WELCOME_TIME
        ):

            phase_elapsed = (
                elapsed -
                INITIALIZING_TIME -
                SYSTEM_TIME
            )

            self.current_frame = (
                self.background.copy()
            )

            self.current_frame.alpha_composite(
                self.soft_light
            )

            self.draw_welcome(
                phase_elapsed
            )

        # ====================================================
        # PHASE 4
        # LOGO
        # ====================================================

        elif elapsed < (
            INITIALIZING_TIME +
            SYSTEM_TIME +
            WELCOME_TIME +
            LOGO_TIME
        ):

            phase_elapsed = (
                elapsed -
                INITIALIZING_TIME -
                SYSTEM_TIME -
                WELCOME_TIME
            )

            self.current_frame = (
                self.background.copy()
            )

            self.current_frame.alpha_composite(
                self.soft_light
            )

            self.draw_logo(
                phase_elapsed
            )

        # ====================================================
        # PHASE 5
        # HOLD LOGO
        # ====================================================

        elif elapsed < (
            INITIALIZING_TIME +
            SYSTEM_TIME +
            WELCOME_TIME +
            LOGO_TIME +
            LOGO_HOLD_TIME
        ):

            self.current_frame = (
                self.background.copy()
            )

            self.current_frame.alpha_composite(
                self.soft_light
            )

            self.draw_logo(
                LOGO_TIME
            )

        # ====================================================
        # FINISH
        # ====================================================

        else:

            self.finished = True

            self.root.destroy()

            return

        # ====================================================
        # DISPLAY FRAME
        # ====================================================

        self.canvas.delete(
            "all"
        )

        photo = ImageTk.PhotoImage(
            self.current_frame
        )

        self.canvas.create_image(
            0,
            0,
            anchor="nw",
            image=photo
        )

        self.canvas.image = photo

        # ====================================================
        # NEXT FRAME
        # ====================================================

        self.root.after(
            int(1000 / FPS),
            self.animate
        )


# ============================================================
# RUN
# ============================================================
def run_intro():
    root = tk.Tk()

    app = AttendXIntro(root)

    root.mainloop()


if __name__ == "__main__":
    run_intro()