# Metro Status Display Deployment

This directory contains the deployment configuration for running the Metro Status Display as a systemd service on a Raspberry Pi.

## Prerequisites

1. Ensure the repository is cloned to `/home/pi/home-stm-metro-status`
2. All Python dependencies are installed:
   ```bash
   pip3 install -r ../requirements.txt
   ```
3. The LED matrix library is properly installed and configured

## Installation

1. Make the deployment script executable:
   ```bash
   chmod +x deploy.sh
   ```

2. Run the deployment script:
   ```bash
   ./deploy.sh
   ```

## Service Management

- Check service status:
  ```bash
  sudo systemctl status metro-status
  ```

- View logs:
  ```bash
  tail -f /var/log/metro-status.log
  tail -f /var/log/metro-status.error.log
  ```

- Restart service:
  ```bash
  sudo systemctl restart metro-status
  ```

- Stop service:
  ```bash
  sudo systemctl stop metro-status
  ```

- Start service:
  ```bash
  sudo systemctl start metro-status
  ```

## Troubleshooting

1. If the service fails to start, check the error logs:
   ```bash
   tail -f /var/log/metro-status.error.log
   ```

2. Verify the LED matrix permissions:
   ```bash
   sudo usermod -a -G gpio pi
   ```

3. Check if the service is enabled:
   ```bash
   systemctl is-enabled metro-status
   ```

4. If you need to modify the service configuration:
   ```bash
   sudo systemctl edit metro-status
   ```

## Uninstallation

To remove the service:

```bash
sudo systemctl stop metro-status
sudo systemctl disable metro-status
sudo rm /etc/systemd/system/metro-status.service
sudo systemctl daemon-reload
sudo rm /var/log/metro-status.log
sudo rm /var/log/metro-status.error.log
``` 