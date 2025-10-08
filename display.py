# display.py - Handles sending images to the correct output.

import time
import os
import threading
from PIL import Image, ImageDraw

# --- Auto-detection of Hardware ---
# The 'try...except' block is the key to this whole system.
IS_PI = False
try:
    # If this import works, we are on a Raspberry Pi with the library installed.
    from rgbmatrix import RGBMatrix, RGBMatrixOptions

    IS_PI = True
    print("Raspberry Pi with RGBMatrix library detected. Using physical display.")
except ImportError:
    # If it fails, we are on a different computer (e.g., your development machine).
    print("Not on a Raspberry Pi. Using file-based simulator.")
# ----------------------------------


class Display:
    """Base class for display types."""

    def start(self):
        pass

    def stop(self):
        pass

    def show(self, images, **kwargs):
        raise NotImplementedError

    def clear(self):
        raise NotImplementedError


class SimulatorDisplay(Display):
    """Saves the image(s) to a file, simulating the display."""

    def __init__(self, save_folder="simulated_displays"):
        self.save_folder = save_folder
        os.makedirs(self.save_folder, exist_ok=True)
        print(f"Simulator active. Images will be saved in '{self.save_folder}/'")

    def _render_to_file_image(self, image, dot_size=4, gap=1):
        """Scales a raw image up into a pretty simulated image file."""
        width, height = image.size
        cell_size = dot_size + gap
        img_width = width * cell_size - gap
        img_height = height * cell_size - gap
        out_image = Image.new("RGB", (img_width, img_height), color="black")
        draw = ImageDraw.Draw(out_image)
        for y in range(height):
            for x in range(width):
                pixel = image.getpixel((x, y))
                if pixel != (0, 0, 0):  # If the pixel is on
                    x0 = x * cell_size
                    y0 = y * cell_size
                    x1 = x0 + dot_size
                    y1 = y0 + dot_size
                    draw.ellipse([(x0, y0), (x1, y1)], fill=pixel)
        return out_image

    def show(self, images, flight_data=None, **kwargs):
        if not flight_data:
            flight_data = {"flight_number": "unknown"}

        if not isinstance(images, list):
            images = [images]

        flight_num = flight_data.get("flight_number", "unknown").replace("/", "-")

        if len(images) > 1:
            # It's an animation
            filename = f"flight_display_{flight_num}.gif"
            full_path = os.path.join(self.save_folder, filename)
            rendered_frames = [self._render_to_file_image(img) for img in images]
            rendered_frames[0].save(
                full_path,
                save_all=True,
                append_images=rendered_frames[1:],
                duration=100,
                loop=0,
                optimize=False,
            )
            print(f"Saved animation to {full_path}")
        else:
            # It's a single static image
            filename = f"flight_display_{flight_num}.png"
            full_path = os.path.join(self.save_folder, filename)
            rendered_image = self._render_to_file_image(images[0])
            rendered_image.save(full_path)
            print(f"Saved image to {full_path}")

    def clear(self):
        print("Simulator: Clearing display (no action needed).")


class MatrixDisplay(Display):
    """Sends the image(s) to a physical RGB LED matrix."""

    def __init__(self):
        self.options = RGBMatrixOptions()
        self.options.rows = 32
        self.options.cols = 64
        self.options.chain_length = 1
        self.options.parallel = 1
        self.options.hardware_mapping = "regular"
        self.options.led_rgb_sequence = "RBG"

        # --- Threading setup ---
        self._frames = []
        self._lock = threading.Lock()
        self._running = threading.Event()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)

    def _run_loop(self):
        """The main loop for the display thread."""
        # Create the matrix object within the thread's context.
        matrix = RGBMatrix(options=self.options)

        # Create an off-screen canvas. We will draw to this, then swap it to the display.
        canvas = matrix.CreateFrameCanvas()

        try:
            while self._running.is_set():
                with self._lock:
                    current_frames = self._frames[:]

                if current_frames:
                    if len(current_frames) > 1:  # Animation
                        for frame in current_frames:
                            if not self._running.is_set():
                                break
                            clean_frame = Image.frombytes(
                                "RGB", frame.size, frame.convert("RGB").tobytes()
                            )
                            canvas.SetImage(clean_frame)
                            canvas = matrix.SwapOnVSync(canvas)
                            time.sleep(0.1)
                    else:  # Static image
                        canvas.SetImage(current_frames[0].convert("RGB"))
                        canvas = matrix.SwapOnVSync(canvas)
                        time.sleep(0.5)
                else:
                    canvas.Clear()
                    canvas = matrix.SwapOnVSync(canvas)
                    time.sleep(0.1)
        finally:
            matrix.Clear()

    def start(self):
        """Starts the background display thread."""
        print("Starting display thread.")
        self._running.set()
        self._thread.start()

    def stop(self):
        """Stops the background display thread."""
        print("Stopping display thread.")
        self._running.clear()
        self._thread.join()  # Wait for the thread to finish cleanly

    def show(self, images, **kwargs):
        """Updates the frames to be displayed by the thread."""
        with self._lock:
            self._frames = images if isinstance(images, list) else [images]

    def clear(self):
        """Clears the frames to be displayed."""
        with self._lock:
            self._frames = []


def get_display():
    """Factory function to get the correct display driver."""
    if IS_PI:
        return MatrixDisplay()
    else:
        return SimulatorDisplay()
