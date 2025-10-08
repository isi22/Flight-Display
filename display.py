# display.py - Handles sending images to the correct output.

import time
from PIL import Image

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


class SimulatorDisplay(Display):
    """Saves the image(s) to a file, simulating the display."""

    def show(self, images, path=None):
        if path is None:
            print("Error: A file path is required for the simulator display.")
            return
        if not isinstance(images, list):
            # It's a single static image
            images.save(path)
            print(f"Simulator saved static image to '{path}'")
        else:
            # It's a list of frames for an animation
            images[0].save(
                path,
                save_all=True,
                append_images=images[1:],
                duration=100,  # ms per frame
                loop=0,
            )
            print(f"Simulator saved animation to '{path}'")


class MatrixDisplay(Display):
    """Sends the image(s) to a physical RGB LED matrix."""

    def __init__(self):
        options = RGBMatrixOptions()
        options.rows = 32
        options.cols = 64
        options.chain_length = 1
        options.parallel = 1
        options.hardware_mapping = "regular"
        self.matrix = RGBMatrix(options=options)

    def show(self, images, path=None):
        if not isinstance(images, list):
            # Display a single static image
            self.matrix.SetImage(images)
            print("Sent static image to LED matrix.")
        else:
            # Loop through and display animation frames
            print("Sending animation to LED matrix... (Press Ctrl+C to stop)")
            try:
                while True:
                    for frame in images:
                        self.matrix.SetImage(frame)
                        time.sleep(0.1)  # Controls scroll speed
            except KeyboardInterrupt:
                print("Animation stopped.")
                self.matrix.Clear()


def get_display():
    """Factory function to get the correct display driver."""
    if IS_PI:
        return MatrixDisplay()
    else:
        return SimulatorDisplay()
