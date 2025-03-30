import time
import sys
import signal
from rgbmatrix import RGBMatrix, RGBMatrixOptions
from PIL import Image, ImageDraw, ImageFont
import json
from datetime import datetime
import logging
import os

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
            "regular"  # Using the same working configuration
        )
        self.options.gpio_slowdown = 4
        self.options.drop_privileges = True  # Using the same working configuration
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

        # Load fonts - prioritize tom-thumb BDF font for LED matrices
        try:
            # Look for tom-thumb BDF font in user's font directory
            bdf_font_paths = [
                "~/.local/share/fonts/tom-thumb.bdf",
                "/home/pi/.local/share/fonts/tom-thumb.bdf",
            ]

            # Try to load BDF font first (best for LED matrix)
            font_loaded = False
            for bdf_path in bdf_font_paths:
                try:
                    # Expand user path if it starts with ~
                    if bdf_path.startswith("~"):
                        bdf_path = os.path.expanduser(bdf_path)

                    # Check if file exists
                    if os.path.exists(bdf_path):
                        # Use fontTools to load BDF font
                        from PIL import BdfFontFile, PcfFontFile, ImageFont

                        # Load the BDF font
                        with open(bdf_path, "rb") as f:
                            p = BdfFontFile.BdfFontFile(f)

                        # Create PIL font from the parsed BDF
                        if hasattr(p, "bdf_info"):
                            logging.info(
                                f"Successfully loaded tom-thumb BDF font: {bdf_path}"
                            )

                            # For BDF fonts, we'll use the custom pixel renderer
                            self.font_small = ImageFont.load(bdf_path)
                            self.font_large = self.font_small  # Same font for both
                            self.using_bdf_font = True
                            font_loaded = True
                            break
                except Exception as e:
                    logging.warning(f"Could not load BDF font {bdf_path}: {e}")
                    continue

            # If BDF font failed, try regular TTF fonts
            if not font_loaded:
                # Font paths for Raspberry Pi OS
                ttf_font_paths = [
                    # Common Raspberry Pi OS font paths
                    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",  # Common on Pi
                    "/usr/share/fonts/truetype/piboto/PibotoLt-Regular.ttf",  # Pi-specific font
                    "/usr/share/fonts/truetype/ttf-dejavu/DejaVuSansMono.ttf",  # Alternative path
                    # Fallback system fonts
                    "/usr/share/fonts/truetype/freefont/FreeMono.ttf",
                    "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
                    # Final fallback - use default font
                    "DejaVuSansMono.ttf",
                ]

                for font_path in ttf_font_paths:
                    try:
                        # Try different font sizes for better LED matrix rendering
                        if font_path == "DejaVuSansMono.ttf":  # Default font
                            self.font_small = ImageFont.truetype(font_path, 5)
                            self.font_large = ImageFont.truetype(font_path, 7)
                        else:  # Specific path
                            self.font_small = ImageFont.truetype(font_path, 5)
                            self.font_large = ImageFont.truetype(font_path, 7)

                        logging.info(f"Successfully loaded TTF font: {font_path}")
                        self.using_bdf_font = False
                        font_loaded = True
                        break
                    except Exception as e:
                        logging.warning(f"Could not load font {font_path}: {e}")
                        continue

            # If no fonts were loaded, use default font as last resort
            if not font_loaded:
                logging.warning("No system fonts found, using fallback pixel font")
                self.font_small = ImageFont.load_default()
                self.font_large = ImageFont.load_default()
                self.using_bdf_font = False
        except Exception as e:
            logging.error(f"Error loading all fonts: {e}")
            # Continue anyway with default font
            self.font_small = ImageFont.load_default()
            self.font_large = ImageFont.load_default()
            self.using_bdf_font = False
            logging.warning("Using PIL default font as fallback")

        # Colors with adjusted brightness for better contrast
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
        """Draw text on the display with pixel-perfect rendering for LED matrix."""
        if font is None:
            font = self.font_small

        # For perfect pixel alignment, ensure x and y are integers
        x, y = int(x), int(y)

        # Special handling for tom-thumb BDF font
        if hasattr(self, "using_bdf_font") and self.using_bdf_font:
            # Draw text in a direct, pixel-by-pixel manner for BDF font
            cursor_x = x
            for char in text:
                try:
                    # Get the bitmap of this character
                    char_bitmap = font.getmask(char)
                    width, height = char_bitmap.size

                    # Draw each pixel
                    for py in range(height):
                        for px in range(width):
                            # Check if this pixel is set in the bitmap
                            pixel_value = char_bitmap.getpixel((px, py))
                            if pixel_value > 0:  # Non-zero pixel value
                                # Draw a single pixel on the image
                                self.draw.point((cursor_x + px, y + py), fill=color)

                    # Move cursor to next character position
                    cursor_x += width + 1  # +1 for spacing
                except Exception as e:
                    logging.warning(f"Error rendering character '{char}': {e}")
                    cursor_x += 4  # Skip ahead in case of error
        elif hasattr(font, "getmask"):
            # TrueType font
            self.draw.text(
                (x, y),
                text,
                fill=color,
                font=font,
                embedded_color=True,
                anchor="lt",
                spacing=0,
            )
        else:
            # Fallback font rendering for other font types
            cursor_x = x
            for char in text:
                bitmap = font.getmask(char)
                w, h = bitmap.size
                for dy in range(h):
                    for dx in range(w):
                        if bitmap.getpixel((dx, dy)) > 0:
                            self.draw.point((cursor_x + dx, y + dy), fill=color)
                cursor_x += w

    def update_display(self, station_data):
        """Update the display with new station data."""
        try:
            # Clear the display
            self.clear()

            # Draw station name (top row) - ensure pixel alignment
            self.draw_text(
                station_data["station_name"],
                0,  # Start at left edge for maximum space
                0,  # Start at top edge for better alignment
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
                0,  # Start at left edge
                8,  # Pixel-aligned position
                period_color,
                self.font_small,
            )

            # Draw line statuses (remaining rows)
            y_pos = 16  # Start position for lines
            for line_number, line_data in station_data["lines"].items():
                # Determine color based on status
                status_color = (
                    self.colors["alert"]
                    if line_data["status"] == "alert"
                    else self.colors["normal"]
                )

                # Create line status text with fixed-width formatting
                line_text = f"{line_data['name'][0]}:{line_data['current_frequency']}"
                if line_data["status"] == "alert":
                    line_text += "!"

                # Draw the line status
                self.draw_text(line_text, 0, y_pos, status_color, self.font_small)
                y_pos += 8  # Increase spacing for better readability

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
