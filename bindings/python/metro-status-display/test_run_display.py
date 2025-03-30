#!/usr/bin/env python3
import unittest
import subprocess
import sys
import os
import signal
import time
import json
import logging
from unittest.mock import patch, MagicMock
from run_display import MetroDisplayRunner

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("test_run_display.log"), logging.StreamHandler()],
)


class TestMetroDisplayRunner(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.runner = MetroDisplayRunner()

    def tearDown(self):
        """Clean up after each test method."""
        self.runner.cleanup()

    def test_initialization(self):
        """Test that the runner initializes correctly."""
        self.assertIsNone(self.runner.metro_process)
        self.assertIsNone(self.runner.display_process)
        self.assertTrue(self.runner.running)

    def test_cleanup(self):
        """Test that cleanup properly terminates processes."""
        # Start dummy processes
        self.runner.metro_process = subprocess.Popen(
            ["sleep", "10"], stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        self.runner.display_process = subprocess.Popen(
            ["sleep", "10"], stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

        # Verify processes are running
        self.assertIsNotNone(self.runner.metro_process.pid)
        self.assertIsNotNone(self.runner.display_process.pid)

        # Clean up
        self.runner.cleanup()

        # Verify processes are terminated
        self.assertIsNotNone(self.runner.metro_process.poll())
        self.assertIsNotNone(self.runner.display_process.poll())

    def test_signal_handler(self):
        """Test that the signal handler properly shuts down the runner."""
        self.runner.signal_handler(signal.SIGTERM, None)
        self.assertFalse(self.runner.running)

    @patch("subprocess.Popen")
    def test_process_monitoring(self, mock_popen):
        """Test that the runner properly monitors child processes."""
        # Mock process objects
        mock_metro = MagicMock()
        mock_display = MagicMock()

        # Configure mocks
        mock_metro.poll.return_value = None
        mock_display.poll.return_value = None
        mock_metro.stderr = MagicMock()
        mock_display.stderr = MagicMock()
        mock_metro.stderr.readline.return_value = ""
        mock_display.stderr.readline.return_value = ""

        # Configure Popen to return our mocks
        mock_popen.side_effect = [mock_display, mock_metro]

        # Start runner in a separate thread
        import threading

        runner_thread = threading.Thread(target=self.runner.run)
        runner_thread.daemon = True
        runner_thread.start()

        # Let it run for a bit
        time.sleep(2)

        # Stop the runner
        self.runner.running = False
        runner_thread.join(timeout=1)

        # Verify processes were started
        self.assertEqual(mock_popen.call_count, 2)

    def test_process_restart(self):
        """Test that processes are restarted when they die."""
        # Start the runner
        self.runner.run()

        # Verify processes are started
        self.assertIsNotNone(self.runner.metro_process)
        self.assertIsNotNone(self.runner.display_process)

        # Kill one process
        self.runner.metro_process.kill()
        time.sleep(6)  # Wait for restart

        # Verify process was restarted
        self.assertIsNotNone(self.runner.metro_process)
        self.assertNotEqual(self.runner.metro_process.poll(), None)


class TestIntegration(unittest.TestCase):
    """Integration tests for the full display system."""

    def setUp(self):
        self.sample_data = {
            "station_name": "Berri-UQAM",
            "current_time_period": "morning_peak",
            "lines": {
                "1": {
                    "name": "Green Line",
                    "current_frequency": "3-5 minutes",
                    "status": "normal",
                },
                "2": {
                    "name": "Orange Line",
                    "current_frequency": "3-5 minutes",
                    "status": "normal",
                },
            },
        }

    def test_full_pipeline(self):
        """Test the full pipeline from metro data to display."""
        # Start the display runner
        runner = MetroDisplayRunner()

        try:
            # Start processes
            runner.display_process = subprocess.Popen(
                [sys.executable, "display.py"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            # Send test data
            json.dump(self.sample_data, runner.display_process.stdin)
            runner.display_process.stdin.write("\n")
            runner.display_process.stdin.flush()

            # Wait for processing
            time.sleep(2)

            # Check process is still running
            self.assertIsNone(runner.display_process.poll())

        finally:
            runner.cleanup()


def run_mock_metro():
    """Run a mock metro process that outputs sample data."""
    sample_data = {
        "station_name": "Berri-UQAM",
        "current_time_period": "morning_peak",
        "lines": {
            "1": {
                "name": "Green Line",
                "current_frequency": "3-5 minutes",
                "status": "normal",
            },
            "2": {
                "name": "Orange Line",
                "current_frequency": "3-5 minutes",
                "status": "normal",
            },
        },
    }

    while True:
        print(json.dumps(sample_data), flush=True)
        time.sleep(30)


def test_manual():
    """Manual test function that can be run directly."""
    logging.info("Starting manual test...")

    # Start the runner
    runner = MetroDisplayRunner()

    try:
        # Run for a minute
        runner.run()
        time.sleep(60)
    except KeyboardInterrupt:
        logging.info("Test interrupted by user")
    finally:
        runner.cleanup()
        logging.info("Manual test completed")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--manual":
        test_manual()
    else:
        unittest.main()
