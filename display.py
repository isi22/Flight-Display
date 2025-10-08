# display.py - Handles sending images to the correct output.

import time
import os

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
    """A base class for display drivers."""

    def show(self, images, path=None):
        raise NotImplementedError

    def clear(self):
        raise NotImplementedError


class SimulatorDisplay(Display):
    """Saves the image(s) to a file, simulating the display."""

    def __init__(self, save_folder="simulated_displays"):
        self.save_folder = save_folder
        os.makedirs(self.save_folder, exist_ok=True)
        print(f"Simulator active. Images will be saved in '{self.save_folder}/'")

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
            images[0].save(
                full_path,
                save_all=True,
                append_images=images[1:],
                duration=100,
                loop=0,
                optimize=False,
            )
            print(f"Saved animation to {full_path}")
        else:
            # It's a single static image
            filename = f"flight_display_{flight_num}.png"
            full_path = os.path.join(self.save_folder, filename)
            images[0].save(full_path)
            print(f"Saved image to {full_path}")

    def clear(self):
        print("Simulator: Clearing display (no action needed).")


class MatrixDisplay(Display):
    """Sends the image(s) to a physical RGB LED matrix."""

    def __init__(self):
        options = RGBMatrixOptions()
        options.rows = 32
        options.cols = 64
        options.chain_length = 1
        options.parallel = 1
        options.hardware_mapping = "regular"
        options.led_rgb_sequence = "RBG"
        self.matrix = RGBMatrix(options=options)

    def show(self, images, **kwargs):
        if not isinstance(images, list):
            images = [images]

        if len(images) > 1:
            # It's an animation, loop through frames
            while True:  # You might want a more sophisticated loop control
                for image in images:
                    self.matrix.SetImage(image.convert("RGB"))
                    time.sleep(0.1)  # Animation speed
        else:
            # It's a single static image
            self.matrix.SetImage(images[0].convert("RGB"))

    def clear(self):
        self.matrix.Clear()


def get_display():
    """Factory function to get the correct display driver."""
    if IS_PI:
        return MatrixDisplay()
    else:
        return SimulatorDisplay()
