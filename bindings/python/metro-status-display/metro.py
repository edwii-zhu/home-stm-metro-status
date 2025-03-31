import requests
import logging
from requests.exceptions import RequestException, HTTPError
from dotenv import load_dotenv
import os
from datetime import datetime, time

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# API configuration
load_dotenv()
API_KEY = os.getenv("STM_API_KEY")
API_SECRET = os.getenv("STM_API_SECRET")
BASE_URL = "https://api.stm.info/pub/od/i3/v2/messages"
ENDPOINT = "/etatservice"
HEADERS = {
    "apiKey": API_KEY,
    "clientSecret": API_SECRET,
    "Accept": "application/json",
}

# Log API configuration (safely)
logging.info(f"API Key present: {bool(API_KEY)}")
logging.info(f"API Secret present: {bool(API_SECRET)}")

# Berri-UQAM station information
BERRI_UQAM = {
    "name": "Berri-UQAM",
    "lines": {"1": "Green Line", "2": "Orange Line"},
    "connections": {
        "1": "Angrignon ↔ Honoré-Beaugrand",
        "2": "Côte-Vertu ↔ Montmorency",
    },
    "operating_hours": {
        "weekday": "5:30 AM - 12:30 AM",
        "weekend": "5:30 AM - 1:00 AM",
    },
    "frequencies": {
        "1": {  # Green Line
            "morning_peak": "2-4 minutes",
            "afternoon_peak": "2-4 minutes",
            "off_peak": "3-5 minutes",
            "late_evening": "8-10 minutes",
            "weekend": "4-8 minutes",
        },
        "2": {  # Orange Line
            "morning_peak": "2-4 minutes",
            "afternoon_peak": "2-4 minutes",
            "off_peak": "3-5 minutes",
            "late_evening": "8-10 minutes",
            "weekend": "4-8 minutes",
        },
    },
}

# Time periods for frequency display
TIME_PERIODS = {
    "morning_peak": "6:30 AM - 9:30 AM",
    "afternoon_peak": "3:30 PM - 6:30 PM",
    "off_peak": "9:30 AM - 3:30 PM",
    "late_evening": "9:00 PM - Close",
}


def is_metro_operating():
    """Check if the metro is currently operating based on the time."""
    current_time = datetime.now().time()
    current_weekday = datetime.now().weekday() < 5  # True for Monday-Friday

    # Parse operating hours
    weekday_start = time(5, 30)  # 5:30 AM
    weekday_end = time(1, 00)  # 12:30 AM (next day)
    weekend_start = time(5, 30)  # 5:30 AM
    weekend_end = time(1, 30)  # 1:00 AM (next day)

    # Log current time for debugging
    day_type = "weekday" if current_weekday else "weekend"
    logging.debug(f"Current time: {current_time}, Day type: {day_type}")

    # Check if current time is within operating hours
    # For times that span midnight, we need to handle them differently
    if current_weekday:
        # For weekdays
        if weekday_start <= current_time:
            # After start time and before midnight
            logging.debug("Metro is operating (weekday, after start time)")
            return True
        elif current_time <= weekday_end:
            # After midnight but before closing time
            logging.debug("Metro is operating (weekday, before end time)")
            return True
    else:
        # For weekends
        if weekend_start <= current_time:
            # After start time and before midnight
            logging.debug("Metro is operating (weekend, after start time)")
            return True
        elif current_time <= weekend_end:
            # After midnight but before closing time
            logging.debug("Metro is operating (weekend, before end time)")
            return True

    logging.debug("Metro is NOT operating (outside of operating hours)")
    return False


def get_current_time_period():
    """Determine the current time period based on the current time."""
    current_time = datetime.now().time()
    current_weekday = datetime.now().weekday() < 5  # True for Monday-Friday

    # First check if it's a weekend
    if not current_weekday:
        return "weekend"

    # For weekdays, determine the time period
    if (
        current_time >= datetime.strptime("06:30", "%H:%M").time()
        and current_time < datetime.strptime("09:30", "%H:%M").time()
    ):
        return "am_peak"
    elif (
        current_time >= datetime.strptime("15:30", "%H:%M").time()
        and current_time < datetime.strptime("18:30", "%H:%M").time()
    ):
        return "pm_peak"
    elif current_time >= datetime.strptime("21:00", "%H:%M").time():
        return "evening"
    else:
        return "off_peak"


def get_station_status():
    """Fetch and parse Berri-UQAM station status from the STM API."""
    url = f"{BASE_URL}{ENDPOINT}"
    try:
        logging.info(f"Making request to: {url}")
        response = requests.get(url, headers=HEADERS, timeout=10)
        logging.info(f"Response status code: {response.status_code}")

        response.raise_for_status()
        data = response.json()

        logging.info("Successfully retrieved data from API")

        # Extract station-specific alerts
        station_alerts = {}

        for alert in data.get("messages", []):
            for entity in alert.get("informed_entities", []):
                route_name = entity.get("route_short_name")
                if route_name in BERRI_UQAM["lines"].keys():
                    # Get the description texts
                    descriptions = alert.get("description_texts", [])
                    header_texts = alert.get("header_texts", [])

                    # Get English descriptions (fallback to French if English not available)
                    description = next(
                        (
                            text["text"]
                            for text in descriptions
                            if text["language"] == "en"
                        ),
                        next(
                            (text["text"] for text in descriptions),
                            "No description available",
                        ),
                    )

                    header = next(
                        (
                            text["text"]
                            for text in header_texts
                            if text["language"] == "en"
                        ),
                        next(
                            (text["text"] for text in header_texts),
                            "No header available",
                        ),
                    )

                    # Get timing information
                    start_time = alert.get("active_periods", {}).get("start")
                    end_time = alert.get("active_periods", {}).get("end")

                    if route_name not in station_alerts:
                        station_alerts[route_name] = {
                            "line_name": BERRI_UQAM["lines"][route_name],
                            "status": description,
                            "header": header,
                            "start_time": start_time,
                            "end_time": end_time,
                        }

        return station_alerts

    except HTTPError as http_err:
        logging.error(f"HTTP error occurred: {http_err}")
        if hasattr(http_err.response, "text"):
            logging.error(f"Response content: {http_err.response.text}")
        return None
    except Exception as e:
        logging.error(f"Error fetching station status: {str(e)}")
        return None


def format_timestamp(timestamp):
    """Convert Unix timestamp to human-readable format."""
    if timestamp:
        return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
    return "No end time specified"


def get_station_data():
    """Get structured data about Berri-UQAM station status."""
    station_alerts = get_station_status()
    current_period = get_current_time_period()

    if station_alerts is None:
        return None

    station_data = {
        "station_name": BERRI_UQAM["name"],
        "operating_hours": BERRI_UQAM["operating_hours"],
        "current_time_period": current_period,
        "lines": {},
    }

    # Add information for each line
    for line_number in sorted(BERRI_UQAM["lines"].keys()):
        line_info = BERRI_UQAM["lines"][line_number]
        connection = BERRI_UQAM["connections"][line_number]
        alert = station_alerts.get(line_number)
        frequencies = BERRI_UQAM["frequencies"][line_number]

        line_data = {
            "name": line_info,
            "route": connection,
            "current_frequency": frequencies[current_period],
            "all_frequencies": frequencies,
            "status": "normal",
        }

        if alert:
            line_data.update(
                {
                    "status": "alert",
                    "alert_description": alert["status"],
                    "alert_header": alert["header"],
                    "alert_start": format_timestamp(alert["start_time"]),
                    "alert_end": format_timestamp(alert["end_time"]),
                }
            )

        station_data["lines"][line_number] = line_data

    return station_data


def display_station_status():
    """Display the current status of Berri-UQAM station in human-readable format."""
    station_data = get_station_data()

    if station_data is None:
        print("Failed to retrieve station status.")
        return

    print("\n=== Berri-UQAM Station Status ===\n")
    print(f"Station: {station_data['station_name']}")
    print("\nOperating Hours:")
    print(f"  Weekdays: {station_data['operating_hours']['weekday']}")
    print(f"  Weekends: {station_data['operating_hours']['weekend']}")
    print("\nConnected Lines:")

    current_period = station_data["current_time_period"]
    period_name = (
        "Weekend" if current_period == "weekend" else TIME_PERIODS[current_period]
    )

    # Display status for each connected line
    for line_number, line_data in station_data["lines"].items():
        print(f"\n{line_data['name']}:")
        print(f"Route: {line_data['route']}")
        print(f"Current Frequency ({period_name}): {line_data['current_frequency']}")

        # Display all frequencies if not weekend
        if current_period != "weekend":
            print("All Frequencies:")
            for period, time_range in TIME_PERIODS.items():
                print(f"  {time_range}: {line_data['all_frequencies'][period]}")
            print(f"  Weekend: {line_data['all_frequencies']['weekend']}")

        print("Status:", end=" ")
        if line_data["status"] == "alert":
            print(line_data["alert_description"])
            print(f"Alert Start: {line_data['alert_start']}")
            print(f"Alert End: {line_data['alert_end']}")
        else:
            print("No current alerts")


def main():
    """Main function to continuously output station data."""
    import json
    import time

    while True:
        try:
            # Check if metro is operating
            if is_metro_operating():
                station_data = get_station_data()
                if station_data:
                    print(json.dumps(station_data), flush=True)
                else:
                    logging.error("Failed to get station data")
                time.sleep(30)  # Update every 30 seconds when metro is operating
            else:
                # Metro is closed, output special closed status
                closed_data = {
                    "station_name": BERRI_UQAM["name"],
                    "operating_hours": BERRI_UQAM["operating_hours"],
                    "current_time_period": "closed",
                    "lines": {},
                    "is_operating": False,
                }
                print(json.dumps(closed_data), flush=True)
                # Sleep longer when metro is closed (5 minutes)
                time.sleep(300)
        except Exception as e:
            logging.error(f"Error in main loop: {e}")
            time.sleep(5)  # Wait a bit before retrying


if __name__ == "__main__":
    main()
