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

        # Try to find and load fonts
        self.load_fonts()

        # Define custom 5x7 pixel font for better LED matrix readability
        self.setup_5x7_font()

        # Colors with adjusted brightness for better contrast
        self.colors = {
            "normal": (0, 255, 0),  # Green
            "weekend": (255, 255, 0),  # Yellow
            "alert": (255, 0, 0),  # Red
            "white": (255, 255, 255),
            "off": (0, 0, 0),
            "green_line": (0, 200, 0),  # Green line color
            "orange_line": (255, 165, 0),  # Orange line color
        }

        # Set up signal handlers
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)

    def try_install_terminus_font(self):
        """Attempt to install the Terminus font if we have permission."""
        try:
            logging.info("Attempting to install Terminus font...")
            # Check if we're running as root (or can use sudo)
            import subprocess
            import os

            # Try both with and without sudo
            cmds = [
                "apt-get update && apt-get install -y fonts-terminus",
                "sudo apt-get update && sudo apt-get install -y fonts-terminus",
            ]

            for cmd in cmds:
                try:
                    logging.info(f"Running: {cmd}")
                    subprocess.check_call(cmd, shell=True)
                    logging.info("Successfully installed Terminus font!")
                    return True
                except subprocess.CalledProcessError as e:
                    logging.warning(f"Command failed: {e}")
                except Exception as e:
                    logging.warning(f"Error running command: {e}")

            # If we get here, both attempts failed
            logging.error("Could not install Terminus font automatically.")
            logging.error("Please run: sudo apt-get install fonts-terminus")
            return False
        except Exception as e:
            logging.error(f"Error attempting to install font: {e}")
            return False

    def load_fonts(self):
        """Load fonts with priority on Terminus pixel fonts."""
        try:
            # First try discovering fonts using fc-list (fontconfig)
            self.discover_fonts_with_fc_list()

            # Try to find Terminus fonts on the system using find command as fallback
            try:
                import subprocess

                # Run find command to locate Terminus fonts on the system
                find_cmd = "find /usr/share/fonts -name '*erminus*' -type f | sort"
                logging.info(f"Searching for Terminus fonts with: {find_cmd}")
                font_locations = subprocess.check_output(
                    find_cmd, shell=True, text=True
                )
                for line in font_locations.splitlines():
                    logging.info(f"Found potential font: {line}")
            except Exception as e:
                logging.warning(f"Could not search for fonts: {e}")

            # Terminus font paths (expanded to include more possible locations for older Raspberry Pi models)
            terminus_font_paths = [
                # Older Raspbian paths (especially for Raspberry Pi 2 Model B)
                "/usr/share/fonts/truetype/ttf-dejavu/Terminus.ttf",
                "/usr/share/fonts/truetype/ttf-bitstream-vera/Terminus.ttf",
                "/usr/share/fonts/X11/misc/ter-u12n.pcf.gz",  # Common PCF terminus on older systems
                "/usr/share/fonts/X11/misc/ter-u16n.pcf.gz",
                "/usr/share/fonts/X11/terminus/ter-u12n.pcf.gz",
                "/usr/share/fonts/X11/terminus/ter-u16n.pcf.gz",
                # Custom installed paths
                "/usr/local/share/fonts/terminus.ttf",
                "/usr/local/share/fonts/Terminus.ttf",
                "/home/pi/.fonts/terminus.ttf",
                "/home/pi/.fonts/Terminus.ttf",
                # Standard paths from before
                "/usr/share/fonts/truetype/terminus/Terminus.ttf",
                "/usr/share/fonts/truetype/terminus-ttf/Terminus.ttf",
                "/usr/share/fonts/truetype/xterm/Terminus.ttf",
                "/usr/share/fonts/truetype/terminus/TerminusTTF-4.39.ttf",
                "/usr/share/fonts/truetype/terminus/TerminusTTF-Bold-4.39.ttf",
                "/usr/share/fonts/X11/PCF/terminus-bold.pcf.gz",
                "/usr/share/fonts/X11/PCF/terminus.pcf.gz",
                "/usr/share/fonts/truetype/terminus/TerminusTTF.ttf",
                "/usr/share/fonts/truetype/terminus/TerminusTTF-Bold.ttf",
            ]

            # Add any discovered font paths
            if hasattr(self, "discovered_fonts"):
                terminus_font_paths = self.discovered_fonts + terminus_font_paths

            # Try to load Terminus font first (best for LED matrix)
            font_loaded = False
            for font_path in terminus_font_paths:
                try:
                    # Check if file exists before trying to load it
                    if not os.path.exists(font_path):
                        continue

                    # For Terminus font, use sizes that work well with LED matrices
                    # Terminus is designed for pixel-perfect rendering
                    if font_path.endswith(".pcf.gz"):
                        # PCF fonts need special handling
                        self.font_small = ImageFont.load(font_path)
                        self.font_large = self.font_small
                    else:
                        # TTF versions can be loaded with different sizes
                        # For older Raspberry Pi with lower resolution, use smaller sizes
                        self.font_small = ImageFont.truetype(
                            font_path, 6
                        )  # Smaller for old Pi
                        self.font_large = ImageFont.truetype(
                            font_path, 10
                        )  # Smaller for old Pi

                    logging.info(
                        f"Successfully loaded Terminus/pixel font: {font_path}"
                    )
                    font_loaded = True
                    self.using_pixel_font = True
                    break
                except Exception as e:
                    continue

            # If no fonts were loaded, use default font as last resort
            if not font_loaded:
                # Just use the default PIL font which should work everywhere
                logging.warning("No system fonts found, using fallback default font")
                self.font_small = ImageFont.load_default()
                self.font_large = ImageFont.load_default()
                self.using_pixel_font = False
        except Exception as e:
            logging.error(f"Error loading all fonts: {e}")
            # Continue anyway with default font
            self.font_small = ImageFont.load_default()
            self.font_large = ImageFont.load_default()
            self.using_pixel_font = False
            logging.warning("Using PIL default font as fallback")

    def discover_fonts_with_fc_list(self):
        """Try to discover font paths using fontconfig's fc-list command."""
        try:
            import subprocess

            # Try using fontconfig to find terminus fonts (more reliable than find)
            try:
                logging.info("Trying to find fonts using fc-list...")
                fc_cmd = "fc-list : file | grep -i terminus"
                font_list = subprocess.check_output(fc_cmd, shell=True, text=True)

                # Parse the output and extract font paths
                self.discovered_fonts = []
                for line in font_list.splitlines():
                    # fc-list output format is usually: /path/to/font.ttf: FontName,Style
                    if ":" in line:
                        font_path = line.split(":", 1)[0].strip()
                        if os.path.exists(font_path):
                            self.discovered_fonts.append(font_path)
                            logging.info(f"Discovered font with fc-list: {font_path}")
            except Exception as e:
                logging.warning(f"fc-list search failed: {e}")

            # If fc-list didn't work, try a simpler approach with fc-match
            if not hasattr(self, "discovered_fonts") or not self.discovered_fonts:
                try:
                    logging.info("Trying fc-match for Terminus...")
                    fc_match_cmd = 'fc-match -v terminus | grep file: | cut -d\\" -f2'
                    font_path = subprocess.check_output(
                        fc_match_cmd, shell=True, text=True
                    ).strip()
                    if font_path and os.path.exists(font_path):
                        self.discovered_fonts = [font_path]
                        logging.info(f"Discovered font with fc-match: {font_path}")
                except Exception as e:
                    logging.warning(f"fc-match search failed: {e}")
                    self.discovered_fonts = []
        except Exception as e:
            logging.warning(f"Font discovery with fontconfig failed: {e}")
            self.discovered_fonts = []

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

    def draw_text(self, text, x, y, color, font=None, background=(0, 0, 0)):
        """Draw text on the display with pixel-perfect rendering for LED matrix."""
        if font is None:
            font = self.font_small

        # For perfect pixel alignment, ensure x and y are integers
        x, y = int(x), int(y)

        # Draw text with optimized parameters for LED matrix
        try:
            # Create a temporary black image for text with exact pixel alignment
            tmp_img = Image.new("RGBA", self.image.size, (0, 0, 0, 0))
            tmp_draw = ImageDraw.Draw(tmp_img)

            # Draw background rectangle for text to improve readability
            text_bbox = tmp_draw.textbbox((x, y), text, font=font)
            # Add padding around text
            padding = 1
            tmp_draw.rectangle(
                [
                    (text_bbox[0] - padding, text_bbox[1] - padding),
                    (text_bbox[2] + padding, text_bbox[3] + padding),
                ],
                fill=background,
            )

            # Draw text with no antialiasing for sharp LED display
            # Add letter_spacing to improve readability
            tmp_draw.text(
                (x, y),
                text,
                fill=color,
                font=font,
                spacing=1,  # Increased spacing between characters
            )

            # Convert the temporary image to RGB and threshold for sharper edges
            tmp_img = tmp_img.convert("RGB")

            # Apply the text image to our main buffer
            for px in range(self.image.width):
                for py in range(self.image.height):
                    pixel = tmp_img.getpixel((px, py))
                    if pixel != (0, 0, 0):  # If not black (background)
                        self.image.putpixel((px, py), pixel)

        except Exception as e:
            logging.error(f"Error drawing text '{text}': {e}")
            # Fallback to default font if there's an error
            try:
                self.draw.text((x, y), text, fill=color)
            except:
                pass  # If even the basic text drawing fails, just continue

    def draw_circle(self, x, y, radius, color):
        """Draw a filled circle at the specified coordinates."""
        x, y = int(x), int(y)
        radius = int(radius)

        # Draw a filled circle using PIL's ellipse drawing
        self.draw.ellipse(
            [(x - radius, y - radius), (x + radius, y + radius)],
            fill=color,
            outline=color,
        )

    def setup_5x7_font(self):
        """Setup custom 5x7 pixel font optimized for LED matrix displays.
        Each character is represented by 5 bytes, each byte for a column of 7 pixels.
        """
        # Define the 5x7 font data - each character is 5 columns of 7 bits
        # Format: Each character is represented by 5 bytes, each byte for a column
        # 1 means LED on, 0 means LED off
        self.font_5x7 = {
            # Numbers
            "0": [0x3E, 0x51, 0x49, 0x45, 0x3E],  # 0
            "1": [0x00, 0x42, 0x7F, 0x40, 0x00],  # 1
            "2": [0x42, 0x61, 0x51, 0x49, 0x46],  # 2
            "3": [0x21, 0x41, 0x45, 0x4B, 0x31],  # 3
            "4": [0x18, 0x14, 0x12, 0x7F, 0x10],  # 4
            "5": [0x27, 0x45, 0x45, 0x45, 0x39],  # 5
            "6": [0x3C, 0x4A, 0x49, 0x49, 0x30],  # 6
            "7": [0x01, 0x71, 0x09, 0x05, 0x03],  # 7
            "8": [0x36, 0x49, 0x49, 0x49, 0x36],  # 8
            "9": [0x06, 0x49, 0x49, 0x29, 0x1E],  # 9
            # Special characters
            "-": [0x08, 0x08, 0x08, 0x08, 0x08],  # -
            ":": [0x00, 0x36, 0x36, 0x00, 0x00],  # :
            "!": [0x00, 0x00, 0x5F, 0x00, 0x00],  # !
            " ": [0x00, 0x00, 0x00, 0x00, 0x00],  # Space
            # Letters - just the ones we need
            "A": [0x7E, 0x11, 0x11, 0x11, 0x7E],  # A
            "D": [0x7F, 0x41, 0x41, 0x41, 0x3E],  # D
            "E": [0x7F, 0x49, 0x49, 0x49, 0x41],  # E
            "F": [0x7F, 0x09, 0x09, 0x09, 0x01],  # F
            "G": [0x3E, 0x41, 0x49, 0x49, 0x3A],  # G
            "I": [0x00, 0x41, 0x7F, 0x41, 0x00],  # I
            "K": [0x7F, 0x08, 0x14, 0x22, 0x41],  # K
            "L": [0x7F, 0x40, 0x40, 0x40, 0x40],  # L
            "M": [0x7F, 0x02, 0x0C, 0x02, 0x7F],  # M
            "N": [0x7F, 0x04, 0x08, 0x10, 0x7F],  # N
            "O": [0x3E, 0x41, 0x41, 0x41, 0x3E],  # O
            "P": [0x7F, 0x09, 0x09, 0x09, 0x06],  # P
            "R": [0x7F, 0x09, 0x19, 0x29, 0x46],  # R
            "T": [0x01, 0x01, 0x7F, 0x01, 0x01],  # T
            "W": [0x7F, 0x20, 0x18, 0x20, 0x7F],  # W
            "Y": [0x07, 0x08, 0x70, 0x08, 0x07],  # Y
        }

        # Add lowercase versions of letters (for convenience)
        lowercase_letters = {}
        for char, pattern in self.font_5x7.items():
            if char.isalpha():
                lowercase_letters[char.lower()] = pattern
        self.font_5x7.update(lowercase_letters)

    def draw_5x7_char(self, x, y, char, color, background=None):
        """Draw a single character from the 5x7 font."""
        if char not in self.font_5x7:
            # Default to space if character not in font
            char = " "

        char_data = self.font_5x7[char]

        # Draw background if specified
        if background:
            self.draw.rectangle([(x, y), (x + 5, y + 7)], fill=background)

        # Draw each column of the character
        for col in range(5):
            column_data = char_data[col]
            for row in range(7):
                # Check if this pixel should be lit (bit is set)
                if column_data & (1 << row):
                    self.draw.point((x + col, y + row), fill=color)

        # Return width of character (5 pixels + 1 pixel spacing)
        return 6

    def draw_5x7_text(self, x, y, text, color, background=None):
        """Draw text using the 5x7 font."""
        cursor_x = x
        for char in text:
            if cursor_x + 5 > self.image.width:  # Stop if we run out of space
                break
            char_width = self.draw_5x7_char(cursor_x, y, char, color, background)
            cursor_x += char_width

        return cursor_x - x  # Return total width

    def update_display(self, station_data):
        """Update the display with new station data."""
        try:
            # Create a double buffer to prevent flicker
            new_image = Image.new("RGB", (64, 32))
            new_draw = ImageDraw.Draw(new_image)

            # Save current drawing surface
            original_draw = self.draw
            original_image = self.image

            # Temporarily set to new buffer
            self.draw = new_draw
            self.image = new_image

            # Clear the buffer
            self.draw.rectangle([(0, 0), (63, 31)], fill=self.colors["off"])

            # Draw time period (first row) with appropriate font size
            period_color = (
                self.colors["weekend"]
                if station_data["current_time_period"] == "weekend"
                else self.colors["white"]
            )

            # Draw time period using 5x7 font
            period_text = station_data["current_time_period"].upper()
            self.draw_5x7_text(2, 2, period_text, period_color)

            # Draw line statuses (remaining rows)
            y_pos = 12  # Start position for line statuses
            line_spacing = 10  # Space between lines

            for line_number, line_data in station_data["lines"].items():
                # Determine alert status for visual indicator
                has_alert = line_data["status"] == "alert"

                # Determine line color based on first letter of the line name
                first_letter = line_data["name"][0].upper()
                circle_color = self.colors["white"]  # Default color

                if first_letter == "G":
                    circle_color = self.colors["green_line"]
                elif first_letter == "O":
                    circle_color = self.colors["orange_line"]

                # Draw colored circle for the line with larger radius for better visibility
                circle_radius = 3
                circle_x = 6
                circle_y = y_pos + 4
                self.draw_circle(circle_x, circle_y, circle_radius, circle_color)

                # Format the frequency text more clearly
                freq = line_data["current_frequency"]
                freq = freq.replace("minutes", "min")
                if has_alert:
                    freq_text = f" {freq}!"
                else:
                    freq_text = f" {freq}"

                # Draw the line status text in white (or red for alerts)
                text_color = self.colors["white"]
                if has_alert:
                    text_color = self.colors["alert"]

                # Draw frequency text using 5x7 font
                self.draw_5x7_text(10, y_pos, freq_text, text_color)

                # Move to next line
                y_pos += line_spacing

            # Restore original drawing surfaces
            self.draw = original_draw
            self.image = original_image

            # Copy the new image to the display buffer all at once (prevents flicker)
            self.image.paste(new_image)

            # Update the display
            self.matrix.SetImage(self.image)

        except Exception as e:
            logging.error(f"Error updating display: {e}")
            self.show_error()

    def show_error(self):
        """Display error state on the LED matrix."""
        try:
            self.clear()

            # Use the best font we have for error display
            if hasattr(self, "using_pixel_font") and self.using_pixel_font:
                # With pixel font, we can show "ERROR" with good clarity
                self.draw_text("ERROR", 12, 12, self.colors["alert"], self.font_large)
            else:
                # With smaller fonts, just show "ERR"
                self.draw_text("ERR", 20, 12, self.colors["alert"], self.font_large)

            self.matrix.SetImage(self.image)
        except Exception as e:
            # If even the error display fails, try a more basic approach
            logging.error(f"Failed to show error screen: {e}")
            try:
                # Try to just set a red color on some pixels
                self.draw.rectangle([(0, 0), (63, 31)], fill=(0, 0, 0))
                self.draw.rectangle([(10, 10), (54, 22)], fill=(255, 0, 0))
                self.matrix.SetImage(self.image)
            except:
                # Last resort - just try to clear the screen
                try:
                    self.matrix.Clear()
                except:
                    pass


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
