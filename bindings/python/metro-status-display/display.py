import time
import sys
import signal
from rgbmatrix import RGBMatrix, RGBMatrixOptions
from PIL import Image, ImageDraw, ImageFont
import json
from datetime import datetime
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
        self.options.hardware_mapping = (
            "regular"  # Changed from adafruit-hat to regular
        )
        self.options.gpio_slowdown = 4
        self.options.drop_privileges = True  # Changed to True for better compatibility
        self.options.brightness = 50  # Adjust brightness (0-100)

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

        # Load fonts
        try:
            self.font_small = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 8
            )
            self.font_large = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 10
            )
        except Exception as e:
            logging.error(f"Error loading fonts: {e}")
            sys.exit(1)

        # Colors
        self.colors = {
            "normal": (0, 255, 0),  # Green
            "weekend": (255, 255, 0),  # Yellow
            "alert": (255, 0, 0),  # Red
            "white": (255, 255, 255),
            "off": (0, 0, 0),
        }

        # Set up signal handlers
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)

    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logging.info("Shutting down display...")
        self.clear()
        self.matrix.Clear()
        sys.exit(0)

    def clear(self):
        """Clear the display."""
        self.draw.rectangle([(0, 0), (63, 31)], fill=self.colors["off"])
        self.matrix.SetImage(self.image)

    def draw_text(self, text, x, y, color, font=None):
        """Draw text on the display."""
        if font is None:
            font = self.font_small
        self.draw.text((x, y), text, fill=color, font=font)

    def update_display(self, station_data):
        """Update the display with new station data."""
        try:
            # Clear the display
            self.clear()

            # Draw station name (top row)
            self.draw_text(
                station_data["station_name"],
                2,
                2,
                self.colors["white"],
                self.font_large,
            )

            # Draw time period (second row)
            period_color = (
                self.colors["weekend"]
                if station_data["current_time_period"] == "weekend"
                else self.colors["white"]
            )
            self.draw_text(
                station_data["current_time_period"].upper(),
                2,
                14,
                period_color,
                self.font_small,
            )

            # Draw line statuses (bottom row)
            y_pos = 24
            for line_number, line_data in station_data["lines"].items():
                # Determine color based on status
                status_color = (
                    self.colors["alert"]
                    if line_data["status"] == "alert"
                    else self.colors["normal"]
                )

                # Create line status text
                line_text = f"{line_data['name'][0]}:{line_data['current_frequency']}"
                if line_data["status"] == "alert":
                    line_text += "!"

                # Draw the line status
                self.draw_text(line_text, 2, y_pos, status_color, self.font_small)
                y_pos += 8

            # Update the display
            self.matrix.SetImage(self.image)

        except Exception as e:
            logging.error(f"Error updating display: {e}")
            self.show_error()

    def show_error(self):
        """Display error state on the LED matrix."""
        self.clear()
        self.draw_text("ERROR", 2, 12, self.colors["alert"], self.font_large)
        self.matrix.SetImage(self.image)


def main():
    """Main function to run the display."""
    display = MetroDisplay()
    logging.info("Display initialized")

    try:
        while True:
            # Read station data from stdin
            try:
                line = sys.stdin.readline()
                if not line:
                    break

                station_data = json.loads(line)
                display.update_display(station_data)

                # Wait before next update
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
