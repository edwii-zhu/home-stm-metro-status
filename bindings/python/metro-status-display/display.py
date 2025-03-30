import time
import sys
import signal
from rgbmatrix import RGBMatrix, RGBMatrixOptions
from PIL import Image, ImageDraw, ImageChops
import json
import logging
import os
import select
import threading

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class MetroDisplay:
    def __init__(self):
        # Matrix configuration - going back to basics
        self.options = RGBMatrixOptions()
        self.options.rows = 32
        self.options.cols = 64
        self.options.chain_length = 1
        self.options.parallel = 1
        self.options.hardware_mapping = "regular"
        self.options.gpio_slowdown = 2  # Increased slowdown to reduce CPU impact
        self.options.drop_privileges = True
        self.options.brightness = 20  # Lower brightness

        # Very simple, default PWM settings
        self.options.pwm_bits = 8  # Lower value
        self.options.pwm_lsb_nanoseconds = 200  # Higher value
        self.options.limit_refresh_rate_hz = 100  # Limit refresh rate
        self.options.scan_mode = 0  # Progressive scan (default)
        self.options.multiplexing = 0  # Default
        self.options.disable_hardware_pulsing = True  # Disable hardware pulsing
        self.options.show_refresh_rate = 0
        self.options.inverse_colors = False

        # Initialize the matrix with error handling
        try:
            self.matrix = RGBMatrix(options=self.options)
            logging.info("Matrix initialized successfully")
        except Exception as e:
            logging.error(f"Failed to initialize matrix: {e}")
            logging.error(
                "Please ensure you have the correct permissions and hardware connected"
            )
            sys.exit(1)

        # Initialize display buffers with visible content
        self.image = Image.new("RGB", (64, 32), (0, 0, 0))  # Pure black background
        self.draw = ImageDraw.Draw(self.image)
        self.prev_image = None

        # Define custom 5x7 pixel font and colors
        self.setup_5x7_font()
        self.setup_colors()

        # Draw initial content to show display is active
        self.draw_5x7_text(5, 12, "LOADING", (255, 255, 255))
        self.matrix.SetImage(self.image)

        # Set up signal handlers
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)

    def setup_colors(self):
        """Setup display colors with standard RGB values."""
        self.colors = {
            "normal": (0, 255, 0),  # Green
            "weekend": (255, 255, 0),  # Yellow
            "alert": (255, 0, 0),  # Red
            "white": (255, 255, 255),
            "off": (0, 0, 0),  # Pure black
            "green_line": (0, 154, 39),  # Green line color
            "orange_line": (238, 125, 0),  # Orange line color
        }

    def setup_5x7_font(self):
        """Setup custom 5x7 pixel font optimized for LED matrix displays."""
        self.font_5x7 = {
            # Numbers
            "0": [0x3E, 0x51, 0x49, 0x45, 0x3E],
            "1": [0x00, 0x42, 0x7F, 0x40, 0x00],
            "2": [0x42, 0x61, 0x51, 0x49, 0x46],
            "3": [0x21, 0x41, 0x45, 0x4B, 0x31],
            "4": [0x18, 0x14, 0x12, 0x7F, 0x10],
            "5": [0x27, 0x45, 0x45, 0x45, 0x39],
            "6": [0x3C, 0x4A, 0x49, 0x49, 0x30],
            "7": [0x01, 0x71, 0x09, 0x05, 0x03],
            "8": [0x36, 0x49, 0x49, 0x49, 0x36],
            "9": [0x06, 0x49, 0x49, 0x29, 0x1E],
            # Special characters
            "-": [0x08, 0x08, 0x08, 0x08, 0x08],
            ":": [0x00, 0x36, 0x36, 0x00, 0x00],
            "!": [0x00, 0x00, 0x5F, 0x00, 0x00],
            " ": [0x00, 0x00, 0x00, 0x00, 0x00],
            # Letters
            "A": [0x7E, 0x11, 0x11, 0x11, 0x7E],
            "B": [0x7F, 0x49, 0x49, 0x49, 0x36],
            "D": [0x7F, 0x41, 0x41, 0x41, 0x3E],
            "E": [0x7F, 0x49, 0x49, 0x49, 0x41],
            "F": [0x7F, 0x09, 0x09, 0x09, 0x01],
            "G": [0x3E, 0x41, 0x49, 0x49, 0x3A],
            "I": [0x00, 0x41, 0x7F, 0x41, 0x00],
            "K": [0x7F, 0x08, 0x14, 0x22, 0x41],
            "L": [0x7F, 0x40, 0x40, 0x40, 0x40],
            "M": [0x7F, 0x02, 0x0C, 0x02, 0x7F],
            "N": [0x7F, 0x04, 0x08, 0x10, 0x7F],
            "O": [0x3E, 0x41, 0x41, 0x41, 0x3E],
            "P": [0x7F, 0x09, 0x09, 0x09, 0x06],
            "R": [0x7F, 0x09, 0x19, 0x29, 0x46],
            "T": [0x01, 0x01, 0x7F, 0x01, 0x01],
            "V": [0x1F, 0x20, 0x40, 0x20, 0x1F],
            "W": [0x7F, 0x20, 0x18, 0x20, 0x7F],
            "Y": [0x07, 0x08, 0x70, 0x08, 0x07],
        }

        # Add lowercase versions of letters
        self.font_5x7.update(
            {k.lower(): v for k, v in self.font_5x7.items() if k.isalpha()}
        )

    def draw_5x7_char(self, x, y, char, color, background=None):
        """Draw a single character from the 5x7 font."""
        if char not in self.font_5x7:
            char = " "

        # Check boundaries to avoid unnecessary drawing
        if x < 0 or x >= self.image.width or y < 0 or y >= self.image.height:
            return 6  # Skip if outside boundaries

        # Draw background if specified (rectangle is faster than individual pixels)
        if background:
            self.draw.rectangle([(x, y), (x + 4, y + 6)], fill=background)

        # Get character data
        char_data = self.font_5x7[char]

        # Pre-calculate coordinates for drawing to reduce calculations in the loop
        for col in range(5):
            column_data = char_data[col]
            x_pos = x + col

            # Skip if column is outside boundaries
            if x_pos >= self.image.width:
                continue

            # Use a more efficient approach - bitshift checking
            if column_data:  # Only process if column has any pixels
                for row in range(7):
                    if column_data & (1 << row):
                        y_pos = y + row
                        if y_pos < self.image.height:
                            self.draw.point((x_pos, y_pos), fill=color)

        return 6  # Character width including spacing

    def draw_5x7_text(self, x, y, text, color, background=None):
        """Draw text using the 5x7 font."""
        # Early exit for empty strings or out-of-bounds text
        if not text or y >= self.image.height or y + 7 < 0 or x >= self.image.width:
            return 0

        cursor_x = x
        for char in text:
            # Stop if we've gone past the right edge
            if cursor_x >= self.image.width:
                break

            # Draw the character and advance cursor
            char_width = self.draw_5x7_char(cursor_x, y, char, color, background)
            cursor_x += char_width

        return cursor_x - x  # Return the width of text drawn

    def clear(self):
        """Clear the display safely."""
        try:
            # Create a blank image
            blank_image = Image.new("RGB", (64, 32), self.colors["off"])

            # Set the image directly - more efficient than drawing first
            self.image = blank_image
            self.matrix.SetImage(self.image)
            self.prev_image = blank_image  # Update cache

            # Also update the draw object for future operations
            self.draw = ImageDraw.Draw(self.image)

            # Small delay to ensure the clear is processed properly
            time.sleep(0.05)
        except Exception as e:
            logging.error(f"Error clearing display: {e}")
            try:
                # Fallback clear method using direct matrix clear
                self.matrix.Clear()
            except:
                pass

    def draw_circle(self, x, y, radius, color):
        """Draw a filled circle at the specified coordinates."""
        self.draw.ellipse(
            [(x - radius, y - radius), (x + radius, y + radius)],
            fill=color,
            outline=color,
        )

    def show_error(self):
        """Display error state on the LED matrix safely."""
        try:
            # Create a new error image rather than modifying current
            error_image = Image.new("RGB", (64, 32), self.colors["off"])
            error_draw = ImageDraw.Draw(error_image)

            # Use a simpler approach - draw a red rectangle with ERROR text
            error_draw.rectangle(
                [(8, 10), (56, 22)], fill=(20, 0, 0)
            )  # Dark red background

            # Temporarily switch drawing surface
            old_draw, old_image = self.draw, self.image
            self.draw, self.image = error_draw, error_image

            # Draw text
            self.draw_5x7_text(14, 12, "ERROR", self.colors["alert"])

            # Switch back
            self.draw, self.image = old_draw, old_image

            # Set the image
            self.matrix.SetImage(error_image)

            # Keep track of the displayed frame
            self.prev_image = error_image
        except Exception as e:
            logging.error(f"Failed to show error screen: {e}")
            try:
                # Last resort - try basic matrix operations
                self.matrix.Clear()
                time.sleep(0.1)
                # This uses a direct matrix method rather than PIL for reliability
                for y in range(10, 22):
                    for x in range(10, 54):
                        self.matrix.SetPixel(x, y, 255, 0, 0)
            except Exception as e2:
                logging.error(f"Critical display failure: {e2}")

    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logging.info("Shutting down display...")
        self.clear()
        self.matrix.Clear()
        sys.exit(0)

    def update_display(self, station_data):
        """Update the display with new station data."""
        try:
            # Check if metro is operating
            if (
                station_data.get("current_time_period") == "closed"
                or station_data.get("is_operating") is False
            ):
                # Turn off display when metro is closed
                self.clear()
                logging.info("Metro is closed, display turned off")
                return

            # Create a new buffer image
            new_image = Image.new("RGB", (64, 32), self.colors["off"])
            new_draw = ImageDraw.Draw(new_image)

            # Save current drawing surface temporarily
            temp_draw, temp_image = self.draw, self.image
            self.draw, self.image = new_draw, new_image

            # Draw time period (first row)
            period_color = (
                self.colors["weekend"]
                if station_data["current_time_period"] == "weekend"
                else self.colors["white"]
            )

            # Draw all elements to the new buffer
            self.draw_5x7_text(
                2, 2, station_data["current_time_period"].upper(), period_color
            )

            # Draw line statuses if lines data exists and is not empty
            if station_data.get("lines") and len(station_data["lines"]) > 0:
                y_pos = 12
                line_spacing = 10

                for line_number, line_data in station_data["lines"].items():
                    # Determine line color and alert status
                    first_letter = line_data["name"][0].upper()
                    circle_color = (
                        self.colors["green_line"]
                        if first_letter == "G"
                        else self.colors["orange_line"]
                    )
                    has_alert = line_data["status"] == "alert"

                    # Draw line indicator
                    self.draw_circle(6, y_pos + 4, 3, circle_color)

                    # Format and draw frequency text
                    freq = line_data["current_frequency"].replace("minutes", "min")
                    freq_text = f" {freq}!" if has_alert else f" {freq}"
                    text_color = (
                        self.colors["alert"] if has_alert else self.colors["white"]
                    )
                    self.draw_5x7_text(10, y_pos, freq_text, text_color)

                    y_pos += line_spacing
            else:
                # No lines data, draw a message
                self.draw_5x7_text(5, 15, "NO DATA", self.colors["white"])

            # Restore original drawing surfaces
            self.draw, self.image = temp_draw, temp_image

            # Check if new image is significantly different from current display
            # Only update the display if needed to prevent unnecessary refreshes
            if (
                self.prev_image is None
                or self._image_difference(new_image, self.prev_image) > 0.05
            ):
                # Update display once - no continuous refreshing
                self.image = new_image
                self.matrix.SetImage(self.image)
                self.prev_image = new_image
                logging.debug("Display updated with new content")
            else:
                logging.debug("Skipping display update - no significant changes")

        except Exception as e:
            logging.error(f"Error updating display: {e}")
            self.show_error()

    def _image_difference(self, img1, img2):
        """Calculate how different two images are (0.0 to 1.0)."""
        if img1.size != img2.size:
            return 1.0  # Different sizes means completely different

        # Convert to grayscale for simpler comparison
        img1_gray = img1.convert("L")
        img2_gray = img2.convert("L")

        # Calculate difference, normalize, and count significant differences
        diff = ImageChops.difference(img1_gray, img2_gray)
        diff_pixels = sum(
            1 for p in diff.getdata() if p > 10
        )  # Threshold for significant difference

        # Return ratio of different pixels
        return diff_pixels / (img1.width * img1.height)

    def _is_empty_image(self, img):
        """Check if image is empty or very close to black."""
        # Sample pixels to check if image has any meaningful content
        sample_points = [
            (2, 2),
            (32, 2),
            (62, 2),
            (2, 16),
            (32, 16),
            (62, 16),
            (2, 30),
            (32, 30),
            (62, 30),
        ]

        for x, y in sample_points:
            if x < img.width and y < img.height:
                pixel = img.getpixel((x, y))
                # Check if pixel has any meaningful brightness
                if max(pixel) > 15:  # Increased threshold
                    return False
        return True


def main():
    """Main function to run the display."""
    display = None
    try:
        # Initialize display with retry mechanism
        retry_count = 0
        max_retries = 3

        while retry_count < max_retries:
            try:
                display = MetroDisplay()
                # Give display time to stabilize after initialization
                time.sleep(1)
                logging.info("Display initialized successfully")
                break
            except Exception as e:
                retry_count += 1
                logging.error(
                    f"Failed to initialize display (attempt {retry_count}/{max_retries}): {e}"
                )
                if retry_count >= max_retries:
                    logging.error("Max retries reached, exiting")
                    sys.exit(1)
                time.sleep(2)  # Wait before retry

        # Initialize update tracking
        last_update_time = 0
        min_update_interval = 30  # Update every 30 seconds
        last_data = None

        # Main processing loop
        try:
            while True:
                try:
                    # Current time
                    current_time = time.time()

                    # Check if it's time to update
                    time_since_last_update = current_time - last_update_time
                    if time_since_last_update >= min_update_interval:
                        # Try to read data from stdin
                        try:
                            # Non-blocking read
                            rlist, _, _ = select.select([sys.stdin], [], [], 0.1)
                            if rlist:
                                chunk = sys.stdin.readline().strip()
                                if chunk:
                                    try:
                                        station_data = json.loads(chunk)
                                        # Validate data minimally - only current_time_period is required
                                        if "current_time_period" in station_data:
                                            # Update display
                                            logging.info(
                                                f"Updating display with data for time period: {station_data['current_time_period']}"
                                            )

                                            # Check if metro is closed
                                            if (
                                                station_data.get("current_time_period")
                                                == "closed"
                                                or station_data.get("is_operating")
                                                is False
                                            ):
                                                logging.info(
                                                    "Metro is closed, turning off display"
                                                )
                                                display.clear()
                                                # Sleep longer when metro is closed
                                                min_update_interval = 300  # Check every 5 minutes when closed
                                            else:
                                                # Metro is operating, display info and use normal interval
                                                min_update_interval = 30  # Normal 30 second updates when operating
                                                display.update_display(station_data)

                                            last_update_time = current_time
                                            last_data = station_data
                                    except json.JSONDecodeError:
                                        logging.warning("Invalid JSON data received")

                            # If time to update but no data or invalid data, check if we should show a waiting message
                            if time_since_last_update > 120 and last_data is None:
                                # Show waiting message
                                wait_img = Image.new("RGB", (64, 32), (0, 0, 0))
                                wait_draw = ImageDraw.Draw(wait_img)
                                display.draw, display.image = wait_draw, wait_img
                                display.draw_5x7_text(5, 12, "WAITING", (0, 255, 0))
                                display.matrix.SetImage(wait_img)
                                logging.info("Showing waiting message")
                        except Exception as e:
                            logging.error(f"Error reading data: {e}")

                    # Sleep for a longer period - no constant refreshing needed
                    time.sleep(
                        3.0
                    )  # Increased sleep time to reduce CPU load and potential flicker

                except Exception as e:
                    logging.error(f"Unexpected error in main loop: {e}")
                    time.sleep(2)

        except KeyboardInterrupt:
            logging.info("Display stopped by user")
        finally:
            # Clean shutdown
            if display:
                try:
                    # Show goodbye message
                    goodbye_img = Image.new("RGB", (64, 32), (0, 0, 0))
                    goodbye_draw = ImageDraw.Draw(goodbye_img)
                    old_draw, old_image = display.draw, display.image
                    display.draw, display.image = goodbye_draw, goodbye_img
                    display.draw_5x7_text(5, 12, "GOODBYE", (0, 100, 255))
                    display.draw, display.image = old_draw, old_image
                    display.matrix.SetImage(goodbye_img)
                    time.sleep(1)
                    display.matrix.Clear()
                    logging.info("Display shut down cleanly")
                except Exception as e:
                    logging.error(f"Error during shutdown: {e}")
                    try:
                        display.matrix.Clear()
                    except:
                        pass

    except Exception as e:
        logging.error(f"Critical error in main: {e}")
        if display:
            try:
                display.matrix.Clear()
            except:
                pass
        sys.exit(1)


if __name__ == "__main__":
    main()
