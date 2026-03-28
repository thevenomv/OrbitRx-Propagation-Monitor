# OrbitRx Propagation Monitor

A professional desktop application for HAM radio operators to monitor real-time space weather data and predict HF radio propagation conditions.

## Features

### Real-Time Space Weather Data
- **Kp Index**: Geomagnetic activity monitoring (0-9 scale)
- **Solar Flux**: 10cm radio wave intensity for propagation estimates
- **Sunspot Number**: Current solar activity levels
- **27-Day Forecast**: F10.7 solar flux predictions
- **Space Weather Alerts**: NOAA space weather alerts

### Propagation Analysis
- **MUF (Maximum Usable Frequency)**: Highest frequency for sky wave propagation
- **LUF (Lowest Usable Frequency)**: Lowest reliable frequency for a given path
- **Band Conditions**: Real-time assessment of 6 HF bands (160m-10m)
- **Sunrise/Sunset Times**: UTC times for optimal propagation windows

### Interactive Map
- **Greyline Visualization**: Day-night terminator line (optimal for DX)
- **Geographic Gridlines**: Latitude/longitude references
- **User Location Marker**: Your position on the world map
- **1600×800 High-Resolution**: Detailed continent and ocean visualization

### Amateur Radio Features
- **DX Spot Log**: Recent distant station contact opportunities
- **Contest Scheduler**: Upcoming HF contests and events
- **Data Logging**: Automatic CSV logging of all readings
- **JSON Export**: Export readings for external analysis
- **History Search**: Lookup dense historical values by date/timestamp/range
- **History Plot**: Visualize Kp/SolarFlux/MUF/LUF trends from logged data

## Getting Started

### Requirements
- Windows 7 or later
- 50 MB disk space
- Internet connection (for real-time data)

### Installation

**Option 1: Standalone Executable (Recommended)**
1. Download `RadioPropagationTracker.exe` from the `dist/` folder
2. Double-click to run
3. No Python installation required

**Option 2: From Source**
1. Install Python 3.14+: https://www.python.org/downloads/
2. Clone or download this repository
3. Run: `py app.py`

### First Run
1. Click **"Refresh Location"** to detect your geographic coordinates
2. Click **"Refresh Space Weather"** to fetch latest NOAA data
3. View the greyline on the map to see optimal propagation zones
4. Check "Help & Guide" button for detailed metric explanations

## User Interface

| Element | Purpose |
|---------|---------|
| **Map (Left)** | World map with greyline, gridlines, and your location |
| **Stats Panel (Right)** | Real-time space weather and propagation metrics |
| **Buttons (Bottom)** | Refresh, export, and help controls |

## Understanding the Metrics

### Kp Index
- **0-3**: Quiet conditions, excellent propagation
- **4-6**: Unsettled, minor degradation
- **7-9**: Major storm, severe propagation loss possible

### Solar Flux
- **60-100**: Low activity, poor long-distance propagation
- **100-150**: Normal conditions
- **150+**: Excellent propagation expected

### Band Conditions
- 🟢 **GREEN (EXCELLENT)**: All bands open, excellent DX conditions
- 🟡 **YELLOW (FAIR)**: Some bands open, limited range
- 🔴 **RED (CLOSED)**: Poor propagation, local-only contacts

### The Greyline
The **orange line** on the map shows where sunrise and sunset occur. This terminator line is where HF propagation is **strongest** because signals can skip off the ionosphere at shallow angles. Best DX contacts occur along the greyline.

## Using the Map

1. **Continents (Green)**: Geographic reference for HF paths
2. **Gridlines**: Latitude/longitude in 15° increments
3. **Cyan Crosshairs**: Equator and Prime Meridian (0° longitude)
4. **Orange Curve**: Day-night boundary (greyline) - aim for this
5. **Green Dot**: Your location (once "Refresh Location" is clicked)

## Data Logging

All readings are automatically logged to `propagation_log.csv`:
- Timestamp (UTC)
- Kp Index
- Solar Flux
- Sunspot Number
- MUF/LUF estimates
- Band Conditions
- Your coordinates

Use this historical data to analyze propagation trends.

## Advanced Tips

### For Best DX Results
1. **Operate on the greyline** - Use the map to find optimal zones
2. **Check solar flux** - Wait for peaks above 150 sfu for long distance
3. **Monitor Kp Index** - Avoid operating during major geomagnetic storms (Kp > 5)
4. **Use sunrise/sunset times** - Plan operating windows around these times
5. **Check band conditions** - Only use bands with green (EXCELLENT) rating

### For Casual Operating
1. Keep the app running in the background for real-time alerts
2. Check band conditions before switching frequencies
3. Use MUF estimate to avoid wasting time on dead frequencies
4. Monitor alerts for sudden space weather changes

## Keyboard Shortcuts
- **Ctrl+Q**: Quit application
- **Ctrl+R**: Refresh space weather data
- **Ctrl+L**: Refresh location
- **Ctrl+H**: Open help guide

## Troubleshooting

### "Location unknown" appears
- Check your internet connection
- Try clicking "Refresh Location" again
- The app uses your public IP to estimate location

### Map not displaying
- Ensure `world_map.jpg` is in the same folder as `app.py`
- If running executable, map should be bundled automatically
- Try restarting the application

### No data showing
- Click "Refresh Space Weather" button
- Check internet connection
- Wait 60 seconds for automatic refresh
- Check NOAA status at: https://www.swpc.noaa.gov/

### CSV file contains strange characters
- The app automatically sanitizes emoji characters for compatibility
- Export as JSON instead for Unicode support

## Data Sources

- **NOAA SWPC**: Real-time space weather data
- **ipinfo.io**: Geolocation services
- **Historical Data**: Internal CSV logging

## File Structure

```
mypythonapp/
├── app.py                      # Main application
├── generate_map.py             # Map generation script
├── world_map.jpg              # High-resolution map image
├── propagation_log.csv        # Historical data log
└── README.md                  # This file
```

## License

Open-source for HAM radio community use.

## Contributing

Ideas for improvements:
- Real DX Cluster API integration
- Daily propagation forecast emails
- Multi-band visualization overlays
- Historical trend graphing
- Beacon frequency recommendations

## Support

For issues or suggestions, check the "Help & Guide" button in the app for detailed explanations of all features and metrics.

---

**Last Updated**: March 28, 2026
**Version**: 1.0 Beta
**Tested On**: Windows 10/11, Python 3.14+
