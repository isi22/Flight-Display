# image_generator.py
# This script's only job is to generate Pillow Image objects.

from PIL import Image, ImageDraw
from fonts.dot_matrix_font import DOT_MATRIX_FONT


class ImageGenerator:
    """Generates dot matrix style images but does not display them."""

    def __init__(self, width=64, height=32):
        self.width = width
        self.height = height
        self.grid = [[0 for _ in range(width)] for _ in range(height)]

    def clear(self):
        self.grid = [[0 for _ in range(self.width)] for _ in range(self.height)]

    def get_text_width(self, text, font=DOT_MATRIX_FONT, scale=1):
        width = 0
        for char in text.upper():
            if char in font:
                width += (len(font[char]) + 1) * scale
        return max(0, width - scale)

    def draw_text(
        self,
        text,
        x_start=0,
        y_start=0,
        font=DOT_MATRIX_FONT,
        scale=1,
        clip_x_start=None,
        clip_x_end=None,
    ):
        x = x_start
        for char in text.upper():
            if char in font:
                char_data = font[char]
                char_width = len(char_data)
                char_height = 7
                for col_index, col_data in enumerate(char_data):
                    for row_index in range(char_height):
                        if (col_data >> row_index) & 1:
                            for sx in range(scale):
                                for sy in range(scale):
                                    draw_x = x + (col_index * scale) + sx
                                    draw_y = y_start + (row_index * scale) + sy
                                    if (
                                        clip_x_start is not None
                                        and draw_x < clip_x_start
                                    ):
                                        continue
                                    if clip_x_end is not None and draw_x >= clip_x_end:
                                        continue
                                    if (
                                        0 <= draw_x < self.width
                                        and 0 <= draw_y < self.height
                                    ):
                                        if char == ":" and scale == 1:
                                            if (
                                                draw_x + 1 < self.width
                                                and draw_y + 1 < self.height
                                            ):
                                                self.grid[draw_y][draw_x] = 1
                                                self.grid[draw_y][draw_x + 1] = 1
                                                self.grid[draw_y + 1][draw_x] = 1
                                                self.grid[draw_y + 1][draw_x + 1] = 1
                                        else:
                                            self.grid[draw_y][draw_x] = 1
                x += (char_width + 1) * scale

    def get_image(self, on_colour=(255, 255, 0)):
        """Converts the internal grid to a correctly sized Pillow Image."""
        image = Image.new("RGB", (self.width, self.height), color="black")
        for y in range(self.height):
            for x in range(self.width):
                if self.grid[y][x] == 1:
                    image.putpixel((x, y), on_colour)
        return image


def get_status_colour(diff_seconds):
    """
    Calculates a colour on a green-yellow-red gradient.
    -1.5 hours (-5400) = Green
    On time (0s)      = Yellow
    +2 hours (+7200s) = Red
    """
    # Define key colours
    green = (0, 255, 0)
    yellow = (255, 255, 0)
    red = (255, 0, 0)

    if diff_seconds <= 0:  # On time or early
        # Scale from Green (-5400) to Yellow (0s)
        # As diff_seconds goes from -5400 to 0, percent goes from 0 to 1
        percent = 1 - (diff_seconds / -3600)
        percent = max(0.0, min(1.0, percent))  # Clamp between 0 and 1

        # Interpolate Red component (Green to Yellow)
        r = int(green[0] * (1 - percent) + yellow[0] * percent)
        g = 255
        b = 0
        return (r, g, b)
    else:  # Delayed
        # Scale from Yellow (0s) to Red (+7200s)
        percent = diff_seconds / 7200.0
        percent = max(0.0, min(1.0, percent))  # Clamp between 0 and 1

        # Interpolate Green component (Yellow to Red)
        r = 255
        g = int(yellow[1] * (1 - percent) + red[1] * percent)
        b = 0
        return (r, g, b)


def generate_display_image(
    flight_number,
    origin_code,
    aircraft_type,
    origin_city,
    time_difference_seconds,
):
    # --- Configuration ---
    MATRIX_WIDTH = 64
    MATRIX_HEIGHT = 32
    ON_COLOUR = get_status_colour(time_difference_seconds)
    margin = 2

    generator = ImageGenerator(width=MATRIX_WIDTH, height=MATRIX_HEIGHT)
    line_1_y, line_2_y, line_3_y = 1, 14, 24

    line_1_left = origin_code
    line_1_right = flight_number
    line_2_text = f"{origin_city}"
    line_3_text = aircraft_type

    max_width = MATRIX_WIDTH - 2 * margin

    width_line_1_right = generator.get_text_width(line_1_right)
    x_pos_line_1_right = MATRIX_WIDTH - width_line_1_right - margin

    width_2 = generator.get_text_width(line_2_text)
    scroll_2 = width_2 > max_width

    if not scroll_2:
        print("City name fits. Generating static PNG...")
        generator.clear()
        # Draw line 1 in two parts for correct alignment
        generator.draw_text(line_1_left, x_start=margin, y_start=line_1_y)
        generator.draw_text(line_1_right, x_start=x_pos_line_1_right, y_start=line_1_y)
        # Draw lines 2 and 3
        generator.draw_text(line_2_text, x_start=margin, y_start=line_2_y)
        generator.draw_text(line_3_text, x_start=margin, y_start=line_3_y)

        display_image = generator.get_image(on_colour=ON_COLOUR)
        return display_image

    else:
        print("One or more lines are too long. Generating scrolling GIF...")
        frames = []

        for i in range(width_2 + 20):
            generator.clear()

            # Line 1
            generator.draw_text(line_1_left, x_start=margin, y_start=line_1_y)
            generator.draw_text(
                line_1_right, x_start=x_pos_line_1_right, y_start=line_1_y
            )

            # Line 2 (scrolling)

            generator.draw_text(
                line_2_text,
                x_start=margin - i,
                y_start=line_2_y,
                clip_x_start=margin,
                clip_x_end=MATRIX_WIDTH - margin,
            )
            generator.draw_text(
                line_2_text,
                x_start=margin - i + width_2 + 20,
                y_start=line_2_y,
                clip_x_start=margin,
                clip_x_end=MATRIX_WIDTH - margin,
            )

            # Line 3
            generator.draw_text(line_3_text, x_start=margin, y_start=line_3_y)

            frame_image = generator.get_image(on_colour=ON_COLOUR)
            frames.append(frame_image)
        return frames
