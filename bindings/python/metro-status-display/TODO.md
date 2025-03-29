# Metro Status LED Display Implementation

## Hardware Requirements
- Raspberry Pi (3 or 4 recommended)
- 64x32 RGB LED Matrix Panel
- Power supply for the LED matrix (5V)
- Jumper wires or HAT/Bonnet for connecting the matrix
- Optional: Case/enclosure for the display

## Software Setup

### 1. Raspberry Pi Setup
- [ ] Install Raspberry Pi OS (latest version)
- [ ] Enable SPI interface: `sudo raspi-config` → Interface Options → SPI → Enable
- [ ] Install required packages:
  ```bash
  sudo apt-get update
  sudo apt-get install python3-dev python3-pip
  ```

### 2. LED Matrix Library Installation
- [ ] Clone the rpi-rgb-led-matrix repository:
  ```bash
  git clone https://github.com/hzeller/rpi-rgb-led-matrix.git
  cd rpi-rgb-led-matrix
  ```
- [ ] Build the library:
  ```bash
  make
  ```
- [ ] Install Python bindings:
  ```bash
  cd bindings/python
  sudo pip3 install -e .
  ```

### 3. Project Setup
- [ ] Create a new directory for the project:
  ```bash
  mkdir metro-status-display
  cd metro-status-display
  ```
- [ ] Copy the existing `metro.py` script
- [ ] Create a new `display.py` script for LED matrix control
- [ ] Create a `requirements.txt` file with dependencies:
  ```
  requests
  python-dotenv
  rpi-rgb-led-matrix
  ```

### 4. LED Display Implementation
- [ ] Create `display.py` with the following features:
  - Initialize LED matrix with correct dimensions (64x32)
  - Create compact layout for displaying:
    - Station name (top row)
    - Current time period (second row)
    - Line statuses (Green and Orange) with frequencies
  - Implement text rendering with appropriate font sizes
  - Add color coding for different statuses:
    - Green: Normal operation
    - Yellow: Weekend service
    - Red: Alerts/issues
  - Add automatic refresh every 30 seconds
  - Implement error state display for API failures

### 5. Integration
- [ ] Modify `metro.py` to:
  - Remove logging to file (keep only essential console output)
  - Add error handling for display-related issues
  - Implement a clean shutdown mechanism
- [ ] Create a main script that:
  - Runs both `metro.py` and `display.py`
  - Handles graceful shutdown
  - Manages the update cycle

### 6. Testing
- [ ] Test the display with sample data
- [ ] Verify text readability at different distances
- [ ] Test error handling and recovery
- [ ] Test power consumption and heat management
- [ ] Test long-term stability

### 7. Deployment
- [ ] Create a systemd service for automatic startup
- [ ] Set up proper error logging
- [ ] Implement watchdog to restart if the display fails
- [ ] Create backup/restore procedures

### 8. Documentation
- [ ] Document hardware connections
- [ ] Create setup instructions
- [ ] Document configuration options
- [ ] Add troubleshooting guide

## Example Display Layout
```
BERRI-UQAM
Weekend

G:4-8m N  O:4-8m N
```

## Notes
- The 64x32 display has limited space, so text must be very concise
- Use abbreviations where possible (e.g., 'm' for minutes, 'N' for Normal)
- Use different colors to indicate status
- Keep font sizes small but readable
- Consider adding simple icons for different status types
- Implement error states for API failures

## Future Enhancements
- [ ] Add weather information
- [ ] Implement multiple station support
- [ ] Add bus information
- [ ] Create web interface for configuration
- [ ] Add support for different display sizes
- [ ] Implement brightness control based on time of day 