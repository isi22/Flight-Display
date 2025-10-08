# display.py - Handles display output, switching between physical and simulated.

import os
import time
import multiprocessing as mp
from PIL import Image, ImageDraw
from queue import Empty

# --- Attempt to import the Raspberry Pi specific library ---
IS_PI = False
try:
    from rgbmatrix import RGBMatrix, RGBMatrixOptions

    IS_PI = True
except ImportError:
    print("Not on a Raspberry Pi. Using file-based simulator.")


def _matrix_process_target(queue, options):
    """
    This function runs in a separate process.
    It initialises the matrix and runs the display loop.
    """
    matrix = RGBMatrix(options=options)
    canvas = matrix.CreateFrameCanvas()

    current_frames = []
    frame_index = 0

    try:
        while True:
            # Check for new data from the main process in a non-blocking way
            try:
                new_frames = queue.get_nowait()
                if new_frames is None:  # Shutdown signal
                    break

                # If we get here, there's new data. Update our state.
                current_frames = new_frames
                frame_index = 0  # Reset animation to the beginning
            except Empty:
                # This is normal, it means no new data. Continue with the current animation.
                pass

            # Now, display the current state
            if current_frames:
                if len(current_frames) > 1:  # It's an animation
                    # Display the current frame
                    canvas.SetImage(current_frames[frame_index].convert("RGB"))
                    canvas = matrix.SwapOnVSync(canvas)

                    # Advance to the next frame, looping if necessary
                    frame_index = (frame_index + 1) % len(current_frames)

                    time.sleep(0.1)  # Animation speed
                else:  # It's a static image
                    canvas.SetImage(current_frames[0].convert("RGB"))
                    canvas = matrix.SwapOnVSync(canvas)
                    time.sleep(0.5)  # Sleep to prevent busy-waiting
            else:
                # No frames to show, keep the panel clear.
                canvas.Clear()
                canvas = matrix.SwapOnVSync(canvas)
                time.sleep(0.1)  # Sleep briefly to prevent busy-waiting
    finally:
        matrix.Clear()


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


class MatrixDisplay(Display):
    """Manages a separate process for sending images to the physical matrix."""

    def __init__(self):
        self.options = RGBMatrixOptions()
        self.options.rows = 32
        self.options.cols = 64
        self.options.chain_length = 1
        self.options.parallel = 1
        self.options.hardware_mapping = "regular"
        self.options.led_rgb_sequence = "RBG"
        self.options.brightness = 50

        # --- Multiprocessing setup ---
        self._queue = mp.Queue()
        self._process = mp.Process(
            target=_matrix_process_target, args=(self._queue, self.options), daemon=True
        )

    def start(self):
        print("Starting display process.")
        self._process.start()

    def stop(self):
        print("Stopping display process.")
        self._queue.put(None)  # Send sentinel to stop the loop
        self._process.join()  # Wait for the process to finish cleanly

    def show(self, images, **kwargs):
        """Sends a new set of frames to the display process."""
        self._queue.put(images if isinstance(images, list) else [images])

    def clear(self):
        """Sends a clear command to the display process."""
        self._queue.put([])


class SimulatorDisplay(Display):
    """Saves the image(s) to a file, simulating the display."""

    def __init__(self, save_folder="simulated_displays"):
        self.save_folder = save_folder
        os.makedirs(self.save_folder, exist_ok=True)
        print(f"Simulator active. Images will be saved in '{self.save_folder}/'")

    def _render_to_file_image(self, image, dot_size=4, gap=1):
        width, height = image.size
        cell_size = dot_size + gap
        img_width = width * cell_size - gap
        img_height = height * cell_size - gap
        out_image = Image.new("RGB", (img_width, img_height), color="black")
        draw = ImageDraw.Draw(out_image)
        for y in range(height):
            for x in range(width):
                pixel = image.getpixel((x, y))
                if pixel != (0, 0, 0):
                    x0 = x * cell_size
                    y0 = y * cell_size
                    x1 = x0 + dot_size
                    y1 = y0 + dot_size
                    draw.ellipse([(x0, y0), (x1, y1)], fill=pixel)
        return out_image

    def show(self, images, flight_data=None, **kwargs):
        if not flight_data:
            flight_data = {"flight_number": "unknown"}

        flight_num = flight_data.get("flight_number", "unknown").replace("/", "-")
        images = images if isinstance(images, list) else [images]

        if len(images) > 1:
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
            filename = f"flight_display_{flight_num}.png"
            full_path = os.path.join(self.save_folder, filename)
            rendered_image = self._render_to_file_image(images[0])
            rendered_image.save(full_path)
            print(f"Saved image to {full_path}")

    def clear(self):
        print("Simulator: Clearing display (no action needed).")


def get_display():
    """Factory function to get the correct display driver."""
    if IS_PI:
        return MatrixDisplay()
    else:
        return SimulatorDisplay()
