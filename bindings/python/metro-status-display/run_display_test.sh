#!/bin/bash

# Simple script to test the display process with mock metro data

echo "Starting display test..."

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 not found. Please install Python 3."
    exit 1
fi

# Run the simple test and pipe output to display.py
python3 test_run_display.py --simple-test | python3 display.py

echo "Test completed." 