# MobileDeck

![MobileDeck Logo](assets/MDDark.png)

## What is MobileDeck?
MobileDeck is a Python script that allows you to turn your mobile device into a fully customizable macro pad similar to a Stream Deck.

## Features
- **Customizable buttons:** Change text, colors, and add images to your buttons
- **Multiple profiles:** Create different button layouts for different applications
- **Button groups:** Organize buttons into groups within each profile
- **Toggle buttons:** Create buttons that can be toggled on or off
- **Key sequence support:** Execute hotkey sequences with a single button
- **Dark/Light mode:** Choose your preferred theme
- **Button layout customization:** Adjust button size and grid layout
- **Local network only:** Everything runs on your local network for security

## Requirements
- Python 3.11 (Untested on other Python versions)
- A computer running Windows, macOS, or Linux
- A mobile device with a web browser
- Both devices on the same local network

## Installation

1. Go to the [Releases](https://github.com/yourusername/mobiledeck/releases) page
2. Download the latest `MobileDeck.zip` file
3. Extract the zip file to a location of your choice
4. Run the `MobileDeck.exe` file
5. When the "Windows protected your PC" message appears, click "More info"
6. Click "Run anyway"
7. If asked by User Account Control, click "Yes"
8. If asked by Windows Firewall, click "Allow"

## How to Use MobileDeck

### First Time Setup

1. Launch the MobileDeck application on your computer
2. When the application starts, you'll see several lines of output in the console
3. **IMPORTANT:** Look for the IP address on the third line of output - this is the one you need to use
   ```
   * Running on all addresses (0.0.0.0)
   * Running on http://127.0.0.1:23843
   * Running on http://192.168.x.x:23843    <- USE THIS IP ADDRESS
   ```
4. On your mobile device, open your web browser and enter the URL exactly as shown on that line:
   ```
   http://192.168.x.x:23843
   ```
5. You should now see the MobileDeck interface on your mobile device

### Video Tutorial

For a visual guide on setting up and using MobileDeck, watch our tutorial:
[MobileDeck Tutorial Video](https://www.youtube.com/watch?v=your_video_id)

### Creating and Managing Buttons

1. On your computer, with MobileDeck running, click the gear icon (⚙️) in the bottom right corner of the web interface
2. Click "Button Management" to open the button configuration window on your computer
3. In the Button Manager window:
   - Create profiles for different applications or use cases
   - Create groups within profiles to organize your buttons
   - Add and configure buttons with:
     - Custom text
     - Background and text colors
     - Optional images
     - Keyboard shortcuts (hotkeys)
     - Multi-step key sequences
     - Toggle functionality
4. Save your changes when finished

### Using MobileDeck on Your Mobile Device

1. Select a profile from the top dropdown menu
2. Select a group from the second dropdown menu
3. Tap any button to trigger its associated keyboard shortcut on your computer
4. For toggle buttons, tap once to activate and tap again to deactivate
5. Access settings by tapping the gear icon to:
   - Switch between light and dark mode
   - Adjust the number of buttons per row
   - Change button dimensions

### Troubleshooting Connection Issues

- If your mobile device cannot connect, verify both devices are on the same network
- Make sure you're using the correct IP address (the second one shown in the console)
- Check if any firewall software is blocking port 23843
- Try restarting the application if buttons become unresponsive

## Security Notice

MobileDeck runs entirely on your local network and doesn't send any data to external servers. As long as you don't port-forward the application port (23843), it remains accessible only to devices on your local network, ensuring 100% privacy and security.

## Contributing

Contributions are welcome! Feel free to submit pull requests or open issues to help improve MobileDeck.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
