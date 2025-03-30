#!/bin/bash

# Simple script to test the display with basic hardcoded data

echo "Starting simple display test..."

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 not found. Please install Python 3."
    exit 1
fi

# Go to the script directory
cd "$(dirname "$0")"

# Run the simple data generator and pipe to display
python3 simple_metro_data.py | python3 display.py

echo "Test completed." 