#!/usr/bin/env python3
import subprocess
import sys
import signal
import logging
import time
import os
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("metro_display.log"), logging.StreamHandler()],
)

# Lock file path
LOCK_FILE = "/tmp/metro_runner.lock"


def check_lock():
    """Check if another instance is running."""
    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE, "r") as f:
                pid = int(f.read().strip())
            # Check if process is still running
            os.kill(pid, 0)
            logging.error(f"Another instance is already running with PID {pid}")
            return False
        except (OSError, ValueError):
            # Process not running or invalid PID
            try:
                os.remove(LOCK_FILE)
            except OSError:
                pass
    return True


def create_lock():
    """Create lock file with current PID."""
    try:
        with open(LOCK_FILE, "w") as f:
            f.write(str(os.getpid()))
        return True
    except OSError as e:
        logging.error(f"Failed to create lock file: {e}")
        return False


def remove_lock():
    """Remove lock file."""
    try:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
    except OSError as e:
        logging.error(f"Failed to remove lock file: {e}")


class MetroDisplayRunner:
    def __init__(self):
        self.metro_process = None
        self.display_process = None
        self.running = True

        # Set up signal handlers
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)

    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logging.info("Shutting down metro display...")
        self.running = False
        self.cleanup()
        remove_lock()

    def cleanup(self):
        """Clean up processes."""
        if self.metro_process:
            self.metro_process.terminate()
            try:
                self.metro_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.metro_process.kill()

        if self.display_process:
            self.display_process.terminate()
            try:
                self.display_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.display_process.kill()

    def run(self):
        """Run the metro display system."""
        logging.info("Starting metro display system...")

        try:
            while self.running:
                # Start the display process
                self.display_process = subprocess.Popen(
                    [sys.executable, "display.py"],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )

                # Start the metro process
                self.metro_process = subprocess.Popen(
                    [sys.executable, "metro.py", "--json"],
                    stdout=self.display_process.stdin,
                    stderr=subprocess.PIPE,
                    text=True,
                )

                # Monitor the processes
                while self.running:
                    # Check if processes are still running
                    if self.metro_process.poll() is not None:
                        logging.error("Metro process died, restarting...")
                        break
                    if self.display_process.poll() is not None:
                        logging.error("Display process died, restarting...")
                        break

                    # Check for errors
                    metro_error = self.metro_process.stderr.readline()
                    if metro_error:
                        logging.error(f"Metro error: {metro_error}")

                    display_error = self.display_process.stderr.readline()
                    if display_error:
                        logging.error(f"Display error: {display_error}")

                    time.sleep(1)

                # Clean up before restart
                self.cleanup()

                # Wait a bit before restarting
                if self.running:
                    logging.info("Restarting in 5 seconds...")
                    time.sleep(5)

        except Exception as e:
            logging.error(f"Unexpected error: {e}")
        finally:
            self.cleanup()
            remove_lock()
            logging.info("Metro display system stopped")


def main():
    """Main function to run the metro display system."""
    # Check if another instance is running
    if not check_lock():
        sys.exit(1)

    # Create lock file
    if not create_lock():
        sys.exit(1)

    try:
        runner = MetroDisplayRunner()
        runner.run()
    finally:
        remove_lock()


if __name__ == "__main__":
    main()
