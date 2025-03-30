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
        # Matrix configuration
        self.options = RGBMatrixOptions()
        self.options.rows = 32
        self.options.cols = 64
        self.options.chain_length = 1
        self.options.parallel = 1
        self.options.hardware_mapping = "regular"
        self.options.gpio_slowdown = 4  # Increased for better stability
        self.options.drop_privileges = True
        self.options.brightness = 70  # Higher brightness to prevent shutoff

        # Simpler PWM settings for stability
        self.options.pwm_bits = 8  # Lower value for simplicity
        self.options.pwm_lsb_nanoseconds = 70  # Lower for faster cycles
        self.options.limit_refresh_rate_hz = 100  # Fast enough to avoid dropout
        self.options.scan_mode = 0  # Progressive scan
        self.options.multiplexing = 0
        self.options.disable_hardware_pulsing = (
            True  # Use software pulsing for consistent display
        )
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
        self.image = Image.new(
            "RGB", (64, 32), (3, 3, 3)
        )  # Slightly brighter background
        self.draw = ImageDraw.Draw(self.image)
        self.prev_image = None  # Store previous frame for caching

        # Define custom 5x7 pixel font and colors
        self.setup_5x7_font()
        self.setup_colors()

        # Draw initial content to show display is active
        self.draw_5x7_text(5, 12, "LOADING", (255, 255, 255), background=(5, 5, 5))
        self.matrix.SetImage(self.image)

        # Force a redraw with a slight delay to keep the display active
        time.sleep(0.5)
        self.matrix.SetImage(self.image)

        # Set up signal handlers
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)

    def setup_colors(self):
        """Setup display colors with adjusted brightness for better contrast."""
        self.colors = {
            "normal": (0, 255, 0),  # Green
            "weekend": (255, 255, 0),  # Yellow
            "alert": (255, 0, 0),  # Red
            "white": (255, 255, 255),
            "off": (3, 3, 3),  # Dark gray instead of black
            "green_line": (0, 154, 39),  # Green line color
            "orange_line": (238, 125, 0),  # Orange line color
            "background": (5, 5, 5),  # Background color for text
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
            # Keep current image as backup
            backup_image = self.image.copy() if self.image else None

            # Create a new buffer image with non-black background
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
                2,
                2,
                station_data["current_time_period"].upper(),
                period_color,
                background=self.colors["background"],  # Add background to text
            )

            # Draw line statuses
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
                text_color = self.colors["alert"] if has_alert else self.colors["white"]
                self.draw_5x7_text(
                    10,
                    y_pos,
                    freq_text,
                    text_color,
                    background=self.colors["background"],
                )  # Add background to text

                y_pos += line_spacing

            # Restore original drawing surfaces
            self.draw, self.image = temp_draw, temp_image

            # Validate the new image
            if self._is_empty_image(new_image):
                logging.error("Generated empty display image, using backup")
                if backup_image:
                    self.matrix.SetImage(backup_image)
                    return

            # Update display
            self.image = new_image
            self.matrix.SetImage(self.image)
            self.prev_image = new_image

            # Set up a delayed redraw to prevent display from turning off
            def delayed_redraw():
                time.sleep(2)  # Wait 2 seconds
                try:
                    # Re-set the image to keep display active
                    self.matrix.SetImage(self.image)
                except Exception as e:
                    logging.error(f"Error in delayed redraw: {e}")

            # Start thread for delayed redraw to keep display active
            threading.Thread(target=delayed_redraw, daemon=True).start()

        except Exception as e:
            logging.error(f"Error updating display: {e}")
            # Don't show error immediately - try to keep current display
            if backup_image:
                try:
                    self.matrix.SetImage(backup_image)
                except:
                    self.show_error()
            else:
                self.show_error()

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
        min_update_interval = 30  # Shorter update interval
        last_data = None

        # Initialize last refresh time for display keep-alive
        last_refresh_time = time.time()
        refresh_interval = (
            1.0  # Refresh every second to prevent display from turning off
        )

        # Main processing loop
        try:
            while True:
                try:
                    # Current time
                    current_time = time.time()

                    # Periodic display refresh to keep display active
                    if current_time - last_refresh_time >= refresh_interval:
                        if display.image:
                            # Refresh current image to keep display active
                            display.matrix.SetImage(display.image)
                            last_refresh_time = current_time

                    # Calculate time since last update
                    time_since_last_update = current_time - last_update_time

                    # Check if we should process new data
                    if time_since_last_update >= min_update_interval:
                        # Read input with timeout to avoid blocking
                        rlist, _, _ = select.select(
                            [sys.stdin], [], [], 0.1
                        )  # Shorter timeout

                        if rlist:
                            # Read a chunk of data
                            chunk = sys.stdin.readline()
                            if not chunk:
                                time.sleep(0.1)  # Short sleep
                                continue

                            # Try to process it as complete JSON
                            try:
                                station_data = json.loads(chunk)

                                # Validate data minimally
                                if (
                                    "current_time_period" not in station_data
                                    or "lines" not in station_data
                                ):
                                    logging.warning(
                                        "Received incomplete station data, skipping update"
                                    )
                                    time.sleep(0.1)  # Short sleep
                                    continue

                                # Update display
                                logging.info("Updating display with new data")
                                display.update_display(station_data)
                                last_update_time = current_time
                                last_data = station_data

                                # Force a small delay after updating
                                time.sleep(0.1)  # Short sleep
                            except json.JSONDecodeError:
                                logging.warning("Received invalid JSON data")
                                time.sleep(0.1)  # Short sleep
                        else:
                            # No data available, sleep briefly
                            time.sleep(0.1)  # Short sleep
                    else:
                        # Not time to update yet - short sleep
                        time.sleep(
                            0.1
                        )  # Short sleep to allow for frequent display refreshes

                        # If it's been a long time since we've seen data, display a message
                        if (
                            current_time - last_update_time > 120 and last_data is None
                        ):  # 2 minutes with no data
                            # Create a waiting display with prominent text
                            wait_image = Image.new("RGB", (64, 32), (3, 3, 3))
                            wait_draw = ImageDraw.Draw(wait_image)

                            # Temporarily switch drawing surface
                            temp_draw, temp_image = display.draw, display.image
                            display.draw, display.image = wait_draw, wait_image

                            # Draw waiting message with background
                            display.draw_5x7_text(
                                5, 12, "WAITING", (0, 255, 0), background=(5, 5, 5)
                            )

                            # Restore drawing surface and update display
                            display.draw, display.image = temp_draw, temp_image
                            display.matrix.SetImage(wait_image)

                            # Update last refresh time since we just refreshed
                            last_refresh_time = current_time

                            # Wait a bit before trying again
                            time.sleep(1)

                except json.JSONDecodeError as e:
                    logging.error(f"Error parsing JSON: {e}")
                    time.sleep(0.5)
                except Exception as e:
                    logging.error(f"Unexpected error in main loop: {e}")
                    time.sleep(0.5)

                    # Ensure display is still active
                    if display and display.image:
                        display.matrix.SetImage(display.image)

        except KeyboardInterrupt:
            logging.info("Display stopped by user")
        finally:
            # Clean shutdown - display a goodbye message before clearing
            if display:
                try:
                    # Create goodbye message
                    goodbye_image = Image.new("RGB", (64, 32), (3, 3, 3))
                    goodbye_draw = ImageDraw.Draw(goodbye_image)

                    # Temporarily switch drawing surface
                    temp_draw, temp_image = display.draw, display.image
                    display.draw, display.image = goodbye_draw, goodbye_image

                    # Draw goodbye message
                    display.draw_5x7_text(
                        2, 12, "GOODBYE", (0, 100, 255), background=(5, 5, 5)
                    )

                    # Restore drawing surface and show message
                    display.draw, display.image = temp_draw, temp_image
                    display.matrix.SetImage(goodbye_image)

                    # Pause briefly to show message
                    time.sleep(1)

                    # Now clear the display
                    display.matrix.Clear()
                    logging.info("Display shut down cleanly")
                except Exception as e:
                    logging.error(f"Error during shutdown: {e}")
                    try:
                        display.matrix.Clear()
                    except:
                        pass

    except Exception as e:
        logging.error(f"Critical error: {e}")
        if display:
            try:
                display.matrix.Clear()
            except:
                pass
        sys.exit(1)


if __name__ == "__main__":
    main()
