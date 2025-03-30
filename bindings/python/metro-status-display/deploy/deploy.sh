#!/bin/bash

# Exit on error
set -e

echo "Starting Metro Status Display deployment..."

# Function to check if running as root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        echo "Please run as root (use sudo)"
        exit 1
    fi
}

# Function to setup log files
setup_logs() {
    echo "Setting up log files..."
    touch /var/log/metro-status.log
    touch /var/log/metro-status.error.log
    chown pi:pi /var/log/metro-status.log
    chown pi:pi /var/log/metro-status.error.log
    chmod 644 /var/log/metro-status.log
    chmod 644 /var/log/metro-status.error.log
}

# Function to setup the systemd service
setup_service() {
    echo "Setting up systemd service..."
    cp metro-status.service /etc/systemd/system/
    systemctl daemon-reload
    systemctl enable metro-status
    systemctl start metro-status
}

# Function to configure hardware
configure_hardware() {
    echo "Configuring hardware..."
    
    # Enable SPI interface
    raspi-config nonint do_spi 0
    
    # Add user to gpio group
    usermod -a -G gpio pi
    
    # Disable sound (if it conflicts with LED matrix)
    echo "blacklist snd_bcm2835" > /etc/modprobe.d/blacklist-rgb-matrix.conf
    update-initramfs -u
}

# Function to verify installation
verify_installation() {
    echo "Verifying installation..."
    
    # Check if service is running
    if systemctl is-active --quiet metro-status; then
        echo "Service is running"
    else
        echo "Service failed to start"
        exit 1
    fi
    
    # Check log files
    if [ -f "/var/log/metro-status.log" ]; then
        echo "Log files created successfully"
    else
        echo "Log files missing"
        exit 1
    fi
}

# Main deployment script
main() {
    echo "=== Metro Status Display Deployment ==="
    
    # Check if running as root
    check_root
    
    # Create backup of current installation if exists
    if [ -d "/home/pi/metro-status-backup" ]; then
        rm -rf /home/pi/metro-status-backup
    fi
    if [ -d "/home/pi/home-stm-metro-status" ]; then
        mv /home/pi/home-stm-metro-status /home/pi/metro-status-backup
    fi
    
    # Run deployment steps
    configure_hardware
    setup_logs
    setup_service
    verify_installation
    
    echo "=== Deployment completed successfully ==="
    echo "You can check the status with: sudo systemctl status metro-status"
    echo "View logs with: tail -f /var/log/metro-status.log"
}

# Run main function
main 