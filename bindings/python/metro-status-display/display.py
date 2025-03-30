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

    def draw_text(self, text, x, y, color, font=None):
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

            # Draw text with no antialiasing for sharp LED display
            tmp_draw.text(
                (x, y),
                text,
                fill=color,
                font=font,
                spacing=0,  # Tight spacing for LED matrix
            )

            # Convert the temporary image to RGB and threshold for sharper edges
            # This step helps create pixel-perfect text by removing antialiasing
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

    def update_display(self, station_data):
        """Update the display with new station data."""
        try:
            # Clear the display
            self.clear()

            # Adjust spacing based on whether we're using a pixel font (Terminus)
            if hasattr(self, "using_pixel_font") and self.using_pixel_font:
                # Terminus font is larger and clearer on LED matrices
                period_y = 2
                lines_start_y = 12
                line_spacing = 8
            else:
                # Smaller TrueType fonts need different spacing
                period_y = 2
                lines_start_y = 10
                line_spacing = 7

            # Draw time period (first row) with appropriate font size
            period_color = (
                self.colors["weekend"]
                if station_data["current_time_period"] == "weekend"
                else self.colors["white"]
            )
            self.draw_text(
                station_data["current_time_period"].upper(),
                1,  # Start slightly offset for cleaner display
                period_y,
                period_color,
                self.font_small,
            )

            # Draw line statuses (remaining rows)
            y_pos = lines_start_y
            for line_number, line_data in station_data["lines"].items():
                # Determine alert status for visual indicator
                has_alert = line_data["status"] == "alert"

                # Determine line color based on line name
                circle_color = self.colors["white"]  # Default color
                if line_data["name"].lower() == "green":
                    circle_color = self.colors["green_line"]
                elif line_data["name"].lower() == "orange":
                    circle_color = self.colors["orange_line"]

                # Draw colored circle for the line
                circle_radius = 2
                circle_x = 3
                circle_y = y_pos + 3
                self.draw_circle(circle_x, circle_y, circle_radius, circle_color)

                # Create line status text with fixed-width formatting
                line_text = f"  {line_data['name'][0]}:{line_data['current_frequency']}"
                if has_alert:
                    line_text += "!"

                # Draw the line status in white (regardless of status)
                text_color = self.colors["white"]
                if has_alert:
                    # For alerts, flash by alternating between red and white
                    current_time = int(time.time())
                    if current_time % 2 == 0:
                        text_color = self.colors["alert"]

                self.draw_text(line_text, 1, y_pos, text_color, self.font_small)
                y_pos += line_spacing  # Adjusted spacing for better readability

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
