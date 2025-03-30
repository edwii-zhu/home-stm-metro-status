#!/usr/bin/env python3
import time
from rgbmatrix import RGBMatrix, RGBMatrixOptions
from PIL import Image, ImageDraw, ImageFont
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("display_test.log"), logging.StreamHandler()],
)


def test_pattern():
    """Display a simple test pattern on the LED matrix."""
    # Matrix configuration
    options = RGBMatrixOptions()
    options.rows = 32
    options.cols = 64
    options.chain_length = 1
    options.parallel = 1
    options.hardware_mapping = "regular"
    options.gpio_slowdown = 4
    options.drop_privileges = True
    options.brightness = 50

    try:
        # Initialize the matrix
        matrix = RGBMatrix(options=options)
        logging.info("Matrix initialized successfully")

        # Create a new image with a black background
        image = Image.new("RGB", (64, 32))
        draw = ImageDraw.Draw(image)

        # Test pattern 1: Solid colors
        colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]  # Red, Green, Blue
        for color in colors:
            logging.info(f"Testing color: {color}")
            draw.rectangle([(0, 0), (63, 31)], fill=color)
            matrix.SetImage(image)
            time.sleep(2)

        # Test pattern 2: Moving rectangle
        for x in range(0, 64, 4):
            draw.rectangle([(0, 0), (63, 31)], fill=(0, 0, 0))  # Clear
            draw.rectangle([(x, 8), (x + 16, 24)], fill=(255, 255, 255))
            matrix.SetImage(image)
            time.sleep(0.1)

        # Test pattern 3: Text
        try:
            font = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 8
            )
        except Exception as e:
            logging.error(f"Error loading font: {e}")
            font = ImageFont.load_default()

        draw.rectangle([(0, 0), (63, 31)], fill=(0, 0, 0))
        draw.text((2, 2), "TEST", fill=(255, 255, 255), font=font)
        matrix.SetImage(image)
        time.sleep(2)

        # Clear the display
        matrix.Clear()
        logging.info("Test pattern completed successfully")

    except Exception as e:
        logging.error(f"Error during test pattern: {e}")
        raise
    finally:
        matrix.Clear()


if __name__ == "__main__":
    test_pattern()
