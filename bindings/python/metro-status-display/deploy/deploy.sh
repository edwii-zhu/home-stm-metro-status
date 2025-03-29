#!/bin/bash

# Exit on error
set -e

# Create log files with appropriate permissions
sudo touch /var/log/metro-status.log
sudo touch /var/log/metro-status.error.log
sudo chown pi:pi /var/log/metro-status.log
sudo chown pi:pi /var/log/metro-status.error.log

# Copy service file to systemd directory
sudo cp metro-status.service /etc/systemd/system/

# Reload systemd to recognize the new service
sudo systemctl daemon-reload

# Enable the service to start on boot
sudo systemctl enable metro-status

# Start the service
sudo systemctl start metro-status

echo "Metro Status service has been installed and started."
echo "You can check the status with: sudo systemctl status metro-status"
echo "View logs with: tail -f /var/log/metro-status.log" 