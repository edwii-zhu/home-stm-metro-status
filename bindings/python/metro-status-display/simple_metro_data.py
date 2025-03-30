#!/usr/bin/env python3
"""
Simple script to generate mock metro data for testing the display.

This script outputs JSON data that matches what the display.py script expects.
It cycles through different time periods, including a closed state.

To use:
    python simple_metro_data.py | python display.py
"""

import json
import time
import sys

# Define hardcoded data for different time periods
SAMPLE_DATA = {
    "normal": {
        "station_name": "Berri-UQAM",
        "operating_hours": {
            "weekday": "5:30 AM - 12:30 AM",
            "weekend": "5:30 AM - 1:00 AM",
        },
        "current_time_period": "am_peak",
        "is_operating": True,
        "lines": {
            "1": {
                "name": "Green Line",
                "route": "Angrignon ↔ Honoré-Beaugrand",
                "current_frequency": "2-4 minutes",
                "all_frequencies": {
                    "am_peak": "2-4 minutes",
                    "pm_peak": "2-4 minutes",
                    "off_peak": "3-5 minutes",
                    "evening": "8-10 minutes",
                    "weekend": "4-8 minutes",
                },
                "status": "normal",
            },
            "2": {
                "name": "Orange Line",
                "route": "Côte-Vertu ↔ Montmorency",
                "current_frequency": "2-4 minutes",
                "all_frequencies": {
                    "am_peak": "2-4 minutes",
                    "pm_peak": "2-4 minutes",
                    "off_peak": "3-5 minutes",
                    "evening": "8-10 minutes",
                    "weekend": "4-8 minutes",
                },
                "status": "normal",
            },
        },
    },
    "alert": {
        "station_name": "Berri-UQAM",
        "operating_hours": {
            "weekday": "5:30 AM - 12:30 AM",
            "weekend": "5:30 AM - 1:00 AM",
        },
        "current_time_period": "pm_peak",
        "is_operating": True,
        "lines": {
            "1": {
                "name": "Green Line",
                "route": "Angrignon ↔ Honoré-Beaugrand",
                "current_frequency": "4-6 minutes",
                "all_frequencies": {
                    "am_peak": "2-4 minutes",
                    "pm_peak": "2-4 minutes",
                    "off_peak": "3-5 minutes",
                    "evening": "8-10 minutes",
                    "weekend": "4-8 minutes",
                },
                "status": "alert",
                "alert_description": "Delays due to signal problem",
                "alert_header": "Service Disruption",
                "alert_start": "2023-08-15 10:30:00",
                "alert_end": "2023-08-15 12:00:00",
            },
            "2": {
                "name": "Orange Line",
                "route": "Côte-Vertu ↔ Montmorency",
                "current_frequency": "2-4 minutes",
                "all_frequencies": {
                    "am_peak": "2-4 minutes",
                    "pm_peak": "2-4 minutes",
                    "off_peak": "3-5 minutes",
                    "evening": "8-10 minutes",
                    "weekend": "4-8 minutes",
                },
                "status": "normal",
            },
        },
    },
    "weekend": {
        "station_name": "Berri-UQAM",
        "operating_hours": {
            "weekday": "5:30 AM - 12:30 AM",
            "weekend": "5:30 AM - 1:00 AM",
        },
        "current_time_period": "weekend",
        "is_operating": True,
        "lines": {
            "1": {
                "name": "Green Line",
                "route": "Angrignon ↔ Honoré-Beaugrand",
                "current_frequency": "4-8 minutes",
                "all_frequencies": {
                    "am_peak": "2-4 minutes",
                    "pm_peak": "2-4 minutes",
                    "off_peak": "3-5 minutes",
                    "evening": "8-10 minutes",
                    "weekend": "4-8 minutes",
                },
                "status": "normal",
            },
            "2": {
                "name": "Orange Line",
                "route": "Côte-Vertu ↔ Montmorency",
                "current_frequency": "4-8 minutes",
                "all_frequencies": {
                    "am_peak": "2-4 minutes",
                    "pm_peak": "2-4 minutes",
                    "off_peak": "3-5 minutes",
                    "evening": "8-10 minutes",
                    "weekend": "4-8 minutes",
                },
                "status": "normal",
            },
        },
    },
    "evening": {
        "station_name": "Berri-UQAM",
        "operating_hours": {
            "weekday": "5:30 AM - 12:30 AM",
            "weekend": "5:30 AM - 1:00 AM",
        },
        "current_time_period": "evening",
        "is_operating": True,
        "lines": {
            "1": {
                "name": "Green Line",
                "route": "Angrignon ↔ Honoré-Beaugrand",
                "current_frequency": "8-10 minutes",
                "all_frequencies": {
                    "am_peak": "2-4 minutes",
                    "pm_peak": "2-4 minutes",
                    "off_peak": "3-5 minutes",
                    "evening": "8-10 minutes",
                    "weekend": "4-8 minutes",
                },
                "status": "normal",
            },
            "2": {
                "name": "Orange Line",
                "route": "Côte-Vertu ↔ Montmorency",
                "current_frequency": "8-10 minutes",
                "all_frequencies": {
                    "am_peak": "2-4 minutes",
                    "pm_peak": "2-4 minutes",
                    "off_peak": "3-5 minutes",
                    "evening": "8-10 minutes",
                    "weekend": "4-8 minutes",
                },
                "status": "normal",
            },
        },
    },
    "closed": {
        "station_name": "Berri-UQAM",
        "operating_hours": {
            "weekday": "5:30 AM - 12:30 AM",
            "weekend": "5:30 AM - 1:00 AM",
        },
        "current_time_period": "closed",
        "is_operating": False,
        "lines": {},
    },
}

# Sequence of modes to cycle through
SEQUENCE = ["normal", "alert", "weekend", "evening", "closed"]


def main():
    """Output JSON data in a loop."""
    print("Simple Metro Data Generator", file=sys.stderr)
    print("-----------------------------", file=sys.stderr)
    print("Cycling through different time periods and states", file=sys.stderr)
    print("Use Ctrl+C to stop", file=sys.stderr)

    index = 0
    try:
        while True:
            # Get the current mode and data
            mode = SEQUENCE[index]
            data = SAMPLE_DATA[mode]

            # Output the JSON to stdout
            json_str = json.dumps(data)
            print(json_str, flush=True)

            # Output info to stderr (won't affect the JSON pipe)
            print(f"Sent {mode} data: {data['current_time_period']}", file=sys.stderr)

            # Move to next mode
            index = (index + 1) % len(SEQUENCE)

            # Wait before sending next data
            time.sleep(8)  # Show each state for 8 seconds

    except KeyboardInterrupt:
        print("\nExiting...", file=sys.stderr)


if __name__ == "__main__":
    main()
