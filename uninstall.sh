#!/bin/bash

# Exit on error
set -e

echo "Starting Metro Status Display uninstallation..."

# Function to check if running as root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        echo "Please run as root (use sudo)"
        exit 1
    fi
}

# Function to remove log files
remove_logs() {
    echo "Removing log files..."
    rm -f /var/log/metro-status.log
    rm -f /var/log/metro-status.error.log
}

# Function to remove the systemd service
remove_service() {
    echo "Removing systemd service..."
    systemctl stop metro-status || true
    systemctl disable metro-status || true
    rm -f /etc/systemd/system/metro-status.service
    systemctl daemon-reload
}

# Function to undo hardware configuration
undo_hardware_config() {
    echo "Undoing hardware configuration..."
    
    # Re-enable sound
    rm -f /etc/modprobe.d/blacklist-rgb-matrix.conf
    update-initramfs -u
    
    # Disable SPI interface (optional - uncomment if needed)
    # raspi-config nonint do_spi 1
}

# Function to restore backup if available
restore_backup() {
    echo "Checking for backup..."
    if [ -d "/home/pi/metro-status-backup" ]; then
        echo "Restoring from backup..."
        rm -rf /home/pi/home-stm-metro-status || true
        mv /home/pi/metro-status-backup /home/pi/home-stm-metro-status
    else
        echo "No backup found."
    fi
}

# Main uninstallation script
main() {
    echo "=== Metro Status Display Uninstallation ==="
    
    # Check if running as root
    check_root
    
    # Run uninstallation steps
    remove_service
    remove_logs
    undo_hardware_config
    restore_backup
    
    echo "=== Uninstallation completed successfully ==="
}

# Run main function
main 