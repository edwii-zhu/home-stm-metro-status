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
from datetime import datetime, timedelta
from freezegun import freeze_time

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


class TestTimePeriodsIntegration(unittest.TestCase):
    """Test the system at different times of day to verify time-based behavior."""

    def setUp(self):
        self.sample_data_generator = SampleDataGenerator()

    @patch("metro.is_metro_operating")
    @patch("metro.get_current_time_period")
    def test_different_time_periods(self, mock_get_period, mock_is_operating):
        """Test system behavior at different times of day."""
        time_periods = [
            # Format: (time, weekday, is_operating, expected_period)
            ("08:00", True, True, "morning_peak"),  # Morning peak (weekday)
            ("14:00", True, True, "off_peak"),  # Off-peak (weekday)
            ("17:00", True, True, "afternoon_peak"),  # Afternoon peak (weekday)
            ("22:00", True, True, "late_evening"),  # Late evening (weekday)
            ("13:00", False, True, "weekend"),  # Weekend
            ("01:30", True, False, "closed"),  # Closed (weekday)
            ("03:00", False, False, "closed"),  # Closed (weekend)
        ]

        for test_time, is_weekday, operating, expected_period in time_periods:
            with self.subTest(time=test_time, weekday=is_weekday, operating=operating):
                # Set mocks to return the correct values
                mock_is_operating.return_value = operating
                mock_get_period.return_value = (
                    expected_period if operating else "closed"
                )

                # Run the test
                self.run_metro_display_test(
                    test_time, is_weekday, operating, expected_period
                )

    def run_metro_display_test(self, test_time, is_weekday, operating, expected_period):
        """Run a test for a specific time period."""
        # Create test data for this time period
        test_data = self.sample_data_generator.generate_data(
            time_period=expected_period, is_operating=operating
        )

        # Log the test configuration
        day_type = "Weekday" if is_weekday else "Weekend"
        operating_status = "Operating" if operating else "Closed"
        logging.info(
            f"Testing: Time={test_time}, {day_type}, {operating_status}, Period={expected_period}"
        )

        # Start the display runner with mocked processes
        with patch("subprocess.Popen") as mock_popen:
            # Mock metro and display processes
            mock_metro = MagicMock()
            mock_display = MagicMock()

            # Configure process behavior
            mock_metro.stdout = MagicMock()
            mock_display.stdin = MagicMock()
            mock_metro.poll.return_value = None
            mock_display.poll.return_value = None

            # Set up pipes for communication
            mock_popen.side_effect = [mock_display, mock_metro]

            # Start the runner
            runner = MetroDisplayRunner()
            import threading

            runner_thread = threading.Thread(target=runner.run)
            runner_thread.daemon = True
            runner_thread.start()

            # Wait a moment for processes to "start"
            time.sleep(1)

            # Simulate metro.py sending data
            metro_output = json.dumps(test_data)
            mock_metro.stdout.readline.return_value = metro_output.encode("utf-8")

            # Run for a longer period (10 seconds per test)
            time.sleep(10)

            # Clean up
            runner.running = False
            runner_thread.join(timeout=2)
            runner.cleanup()

            # Verify the display received appropriate data
            if operating:
                # Verify the display received data in operating mode
                self.assertIn(
                    expected_period, str(mock_display.stdin.write.call_args_list)
                )
            else:
                # Verify the display received closed status
                self.assertIn("closed", str(mock_display.stdin.write.call_args_list))


class TestLongRunning(unittest.TestCase):
    """Long-running tests to verify system stability."""

    def test_day_simulation(self):
        """Simulate a full day of operation with different time periods."""
        # Define time periods to test in sequence
        time_sequence = [
            # Format: (time, duration_minutes, is_operating, expected_period)
            ("03:00", 30, False, "closed"),  # Closed (early morning)
            ("05:40", 30, True, "off_peak"),  # Early morning operation
            ("07:00", 60, True, "morning_peak"),  # Morning peak
            ("12:00", 60, True, "off_peak"),  # Off-peak (midday)
            ("17:00", 60, True, "afternoon_peak"),  # Afternoon peak
            ("21:30", 60, True, "late_evening"),  # Late evening
            ("00:30", 30, True, "late_evening"),  # Late night (still operating)
            ("01:30", 30, False, "closed"),  # Closed (overnight)
        ]

        # Run the simulation
        self.simulate_time_sequence(time_sequence)

    def simulate_time_sequence(self, time_sequence):
        """Run a simulation of the system for a sequence of time periods."""
        sample_data_generator = SampleDataGenerator()

        # Initialize runner with mocked processes
        with patch("subprocess.Popen") as mock_popen:
            mock_metro = MagicMock()
            mock_display = MagicMock()

            # Configure process mocks
            mock_metro.stdout = MagicMock()
            mock_display.stdin = MagicMock()
            mock_metro.poll.return_value = None
            mock_display.poll.return_value = None

            # Set up popen to return our mocks
            mock_popen.side_effect = [mock_display, mock_metro]

            # Start the runner
            runner = MetroDisplayRunner()
            import threading

            runner_thread = threading.Thread(target=runner.run)
            runner_thread.daemon = True
            runner_thread.start()

            # Run through the time sequence
            for (
                test_time,
                duration_minutes,
                operating,
                expected_period,
            ) in time_sequence:
                with patch("metro.is_metro_operating") as mock_is_operating, patch(
                    "metro.get_current_time_period"
                ) as mock_get_period:

                    # Set mock returns
                    mock_is_operating.return_value = operating
                    mock_get_period.return_value = (
                        expected_period if operating else "closed"
                    )

                    # Generate data for this time period
                    test_data = sample_data_generator.generate_data(
                        time_period=expected_period, is_operating=operating
                    )

                    # Log current test state
                    logging.info(
                        f"Simulating time: {test_time}, Operating: {operating}, Period: {expected_period}"
                    )

                    # Simulate metro output
                    metro_output = json.dumps(test_data)
                    mock_metro.stdout.readline.return_value = metro_output.encode(
                        "utf-8"
                    )

                    # Run for the specified duration
                    logging.info(
                        f"Running for {duration_minutes} minutes of simulated time"
                    )

                    # For longer tests, we'll update every 10 seconds to keep the test responsive
                    update_interval = 10  # seconds
                    updates_count = int((duration_minutes * 60) / update_interval)

                    for i in range(updates_count):
                        # Simulate time passing
                        time.sleep(update_interval / 10)  # Scale down for test speed

                        # Occasionally vary the data slightly (like alerts)
                        if i % 3 == 0 and operating:
                            varied_data = sample_data_generator.generate_data(
                                time_period=expected_period,
                                is_operating=operating,
                                add_alert=(i % 6 == 0),  # Add alert every 6th update
                            )
                            metro_output = json.dumps(varied_data)
                            mock_metro.stdout.readline.return_value = (
                                metro_output.encode("utf-8")
                            )

            # Clean up
            runner.running = False
            runner_thread.join(timeout=2)
            runner.cleanup()


class SampleDataGenerator:
    """Generate sample data for testing."""

    def generate_data(
        self, time_period="morning_peak", is_operating=True, add_alert=False
    ):
        """Generate sample data for the specified time period."""
        if not is_operating:
            return {
                "station_name": "Berri-UQAM",
                "operating_hours": {
                    "weekday": "5:30 AM - 12:30 AM",
                    "weekend": "5:30 AM - 1:00 AM",
                },
                "current_time_period": "closed",
                "lines": {},
                "is_operating": False,
            }

        # Define frequencies based on time period
        frequencies = {
            "morning_peak": "2-4 minutes",
            "afternoon_peak": "2-4 minutes",
            "off_peak": "3-5 minutes",
            "late_evening": "8-10 minutes",
            "weekend": "4-8 minutes",
        }

        # Basic data structure
        data = {
            "station_name": "Berri-UQAM",
            "operating_hours": {
                "weekday": "5:30 AM - 12:30 AM",
                "weekend": "5:30 AM - 1:00 AM",
            },
            "current_time_period": time_period,
            "is_operating": True,
            "lines": {
                "1": {
                    "name": "Green Line",
                    "route": "Angrignon ↔ Honoré-Beaugrand",
                    "current_frequency": frequencies.get(time_period, "3-5 minutes"),
                    "all_frequencies": {
                        "morning_peak": "2-4 minutes",
                        "afternoon_peak": "2-4 minutes",
                        "off_peak": "3-5 minutes",
                        "late_evening": "8-10 minutes",
                        "weekend": "4-8 minutes",
                    },
                    "status": "normal",
                },
                "2": {
                    "name": "Orange Line",
                    "route": "Côte-Vertu ↔ Montmorency",
                    "current_frequency": frequencies.get(time_period, "3-5 minutes"),
                    "all_frequencies": {
                        "morning_peak": "2-4 minutes",
                        "afternoon_peak": "2-4 minutes",
                        "off_peak": "3-5 minutes",
                        "late_evening": "8-10 minutes",
                        "weekend": "4-8 minutes",
                    },
                    "status": "normal",
                },
            },
        }

        # Add alert if requested
        if add_alert:
            data["lines"]["1"].update(
                {
                    "status": "alert",
                    "alert_description": "Delays due to signal problem",
                    "alert_header": "Service Disruption",
                    "alert_start": "2023-08-15 10:30:00",
                    "alert_end": "2023-08-15 12:00:00",
                }
            )

        return data


def run_mock_metro(extended=False, duration_minutes=5):
    """Run a mock metro process that outputs sample data."""
    data_generator = SampleDataGenerator()

    # Define time periods to simulate
    if extended:
        time_periods = [
            "morning_peak",
            "off_peak",
            "afternoon_peak",
            "late_evening",
            "weekend",
            "closed",
        ]
    else:
        time_periods = ["morning_peak", "off_peak"]

    end_time = time.time() + (duration_minutes * 60)
    period_index = 0

    while time.time() < end_time:
        # Get the current period to simulate
        current_period = time_periods[period_index]
        is_operating = current_period != "closed"

        # Generate data
        sample_data = data_generator.generate_data(
            time_period=current_period,
            is_operating=is_operating,
            add_alert=(period_index % 3 == 0),  # Add alert every 3rd period
        )

        # Output data
        print(json.dumps(sample_data), flush=True)

        # Sleep for a bit
        time.sleep(10)  # Update every 10 seconds

        # Move to next period occasionally
        if time.time() % 30 < 0.5:  # Switch approximately every 30 seconds
            period_index = (period_index + 1) % len(time_periods)
            logging.info(f"Switching to period: {time_periods[period_index]}")


def test_manual(extended=False, duration_minutes=10):
    """Manual test function that can be run directly."""
    logging.info(
        f"Starting manual test (extended={extended}, duration={duration_minutes} min)..."
    )

    # Start the runner
    runner = MetroDisplayRunner()

    try:
        # Override the metro process to use our mock
        runner.metro_process = subprocess.Popen(
            [
                sys.executable,
                __file__,
                "--mock-metro",
                "--extended" if extended else "",
                "--duration",
                str(duration_minutes),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # Start the display process
        runner.display_process = subprocess.Popen(
            [sys.executable, "display.py"],
            stdin=runner.metro_process.stdout,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Monitor processes
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)

        logging.info(f"Test running for {duration_minutes} minutes...")

        while time.time() < end_time and runner.running:
            # Check if processes are still running
            if runner.metro_process.poll() is not None:
                logging.error("Metro process terminated unexpectedly")
                break

            if runner.display_process.poll() is not None:
                logging.error("Display process terminated unexpectedly")
                break

            # Log progress every minute
            elapsed = time.time() - start_time
            if int(elapsed) % 60 == 0 and int(elapsed) > 0:
                minutes_elapsed = int(elapsed / 60)
                logging.info(f"Test running for {minutes_elapsed} minutes...")

            time.sleep(1)

    except KeyboardInterrupt:
        logging.info("Test interrupted by user")
    finally:
        runner.cleanup()
        logging.info("Manual test completed")


if __name__ == "__main__":
    if "--mock-metro" in sys.argv:
        # This is being run as a mock metro process
        extended = "--extended" in sys.argv
        duration = 5  # Default duration

        if "--duration" in sys.argv:
            try:
                duration_index = sys.argv.index("--duration") + 1
                if duration_index < len(sys.argv):
                    duration = int(sys.argv[duration_index])
            except (ValueError, IndexError):
                pass

        run_mock_metro(extended=extended, duration_minutes=duration)
    elif "--manual" in sys.argv:
        # Run manual test
        extended = "--extended" in sys.argv
        duration = 10  # Default duration

        if "--duration" in sys.argv:
            try:
                duration_index = sys.argv.index("--duration") + 1
                if duration_index < len(sys.argv):
                    duration = int(sys.argv[duration_index])
            except (ValueError, IndexError):
                pass

        test_manual(extended=extended, duration_minutes=duration)
    else:
        # Run automated tests
        unittest.main()
