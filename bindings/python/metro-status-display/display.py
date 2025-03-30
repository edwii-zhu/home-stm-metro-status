import time
import sys
import signal
from rgbmatrix import RGBMatrix, RGBMatrixOptions
from PIL import Image, ImageDraw
import json
import logging

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
        self.options.gpio_slowdown = 4
        self.options.drop_privileges = True
        self.options.brightness = 50

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

        self.image = Image.new("RGB", (64, 32))
        self.draw = ImageDraw.Draw(self.image)

        # Define custom 5x7 pixel font and colors
        self.setup_5x7_font()
        self.setup_colors()

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
            "off": (0, 0, 0),
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

        if background:
            self.draw.rectangle([(x, y), (x + 5, y + 7)], fill=background)

        char_data = self.font_5x7[char]
        for col in range(5):
            column_data = char_data[col]
            for row in range(7):
                if column_data & (1 << row):
                    self.draw.point((x + col, y + row), fill=color)

        return 6  # Character width including spacing

    def draw_5x7_text(self, x, y, text, color, background=None):
        """Draw text using the 5x7 font."""
        cursor_x = x
        for char in text:
            if cursor_x + 5 > self.image.width:
                break
            cursor_x += self.draw_5x7_char(cursor_x, y, char, color, background)
        return cursor_x - x

    def clear(self):
        """Clear the display."""
        self.draw.rectangle([(0, 0), (63, 31)], fill=self.colors["off"])
        self.matrix.SetImage(self.image)

    def draw_circle(self, x, y, radius, color):
        """Draw a filled circle at the specified coordinates."""
        self.draw.ellipse(
            [(x - radius, y - radius), (x + radius, y + radius)],
            fill=color,
            outline=color,
        )

    def show_error(self):
        """Display error state on the LED matrix."""
        try:
            self.clear()
            self.draw_5x7_text(12, 12, "ERROR", self.colors["alert"])
            self.matrix.SetImage(self.image)
        except Exception as e:
            logging.error(f"Failed to show error screen: {e}")
            try:
                self.draw.rectangle([(0, 0), (63, 31)], fill=(0, 0, 0))
                self.draw.rectangle([(10, 10), (54, 22)], fill=(255, 0, 0))
                self.matrix.SetImage(self.image)
            except:
                self.matrix.Clear()

    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logging.info("Shutting down display...")
        self.clear()
        self.matrix.Clear()
        sys.exit(0)

    def update_display(self, station_data):
        """Update the display with new station data."""
        try:
            # Create a new buffer image
            new_image = Image.new("RGB", (64, 32))
            new_draw = ImageDraw.Draw(new_image)

            # Fill the new buffer with black
            new_draw.rectangle([(0, 0), (63, 31)], fill=self.colors["off"])

            # Draw time period (first row)
            period_color = (
                self.colors["weekend"]
                if station_data["current_time_period"] == "weekend"
                else self.colors["white"]
            )

            # Save current drawing surface temporarily
            temp_draw, temp_image = self.draw, self.image
            self.draw, self.image = new_draw, new_image

            # Draw all elements to the new buffer
            self.draw_5x7_text(
                2, 2, station_data["current_time_period"].upper(), period_color
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
                self.draw_5x7_text(10, y_pos, freq_text, text_color)

                y_pos += line_spacing

            # Restore original drawing surfaces
            self.draw, self.image = temp_draw, temp_image

            # Atomically update the display with the new frame
            self.image = new_image
            self.matrix.SetImage(self.image)

        except Exception as e:
            logging.error(f"Error updating display: {e}")
            self.show_error()


def main():
    """Main function to run the display."""
    display = MetroDisplay()
    logging.info("Display initialized")

    try:
        while True:
            try:
                line = sys.stdin.readline()
                if not line:
                    break

                station_data = json.loads(line)
                display.update_display(station_data)
                time.sleep(30)

            except json.JSONDecodeError as e:
                logging.error(f"Error parsing JSON: {e}")
                display.show_error()
                time.sleep(5)
            except Exception as e:
                logging.error(f"Unexpected error: {e}")
                display.show_error()
                time.sleep(5)

    except KeyboardInterrupt:
        logging.info("Display stopped by user")
    finally:
        display.clear()
        display.matrix.Clear()


if __name__ == "__main__":
    main()
