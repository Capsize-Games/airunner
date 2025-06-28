# Map Widget Module

This module provides a Qt widget for displaying and interacting with a Leaflet.js map inside a QWebEngineView, with a Qt sidebar containing map controls for location search and user location.

## Key Components

- **map_widget.py**: Python widget class with Qt sidebar controls. Exposes `add_marker(lat, lon)` and `center_map(lat, lon, zoom=13)` methods for map control.
- **map.ui**: Qt Designer template with sidebar containing search controls and web view for the map.
- **map.jinja2.html**: Simplified HTML template for the map. Loads static CSS/JS without embedded controls.
- **map.js**: JavaScript file. Implements a `MapAPI` class and listens for commands from Python via the BrowserAPI.
- **map.css**: CSS file for map styling.

## UI Layout

The widget uses a horizontal layout with:
- **Left sidebar** (250px fixed width): Contains search controls
  - Search location input field
  - Search button
  - Locate Me button (uses user's current location)
- **Right area**: QWebEngineView displaying the Leaflet map

## Usage

1. **Python API**
   - Call `add_marker(lat, lon)` to add a marker at the specified coordinates.
   - Call `center_map(lat, lon, zoom=13)` to center the map.
   - Enter location in search field and press Enter or click Search button.
   - Click "Locate Me" to center map on user's current location.

2. **Communication**
   - Uses the same BrowserAPI (`api.js`) as the game/browser widgets for robust JS-Python messaging.
   - Qt controls communicate directly with Python methods.
   - All JS and CSS are loaded as static files; no inline code in the HTML.

## Extending
- To add more map features, extend the `MapAPI` class in `map.js` and add corresponding Python methods in `MapWidget`.
- To add more sidebar controls, edit `map.ui` with Qt Designer and regenerate with `airunner-build-ui`.

## Example

```python
widget = MapWidget()
widget.center_map(40.7128, -74.0060, zoom=12)
widget.add_marker(40.7128, -74.0060)
```

## See Also
- [Browser Widget API Documentation](../../browser/gui/static/js/api.js)
- [Leaflet.js Documentation](https://leafletjs.com/)

## Key Components
- **MapWidget**: Main widget for map display and interaction. Integrates with the LLM API for map search.
- **MapWidgetHandler**: Handles communication between JavaScript and Python, including receiving search queries from the frontend.

## Map Search Workflow
1. User enters a search query in the map widget's search input (frontend/JS).
2. The query is sent to Python via the web channel and handled by `MapWidgetHandler.onSearchRequested`.
3. `MapWidgetHandler` calls `MapWidget.handle_map_search`, which invokes the LLM API service (`self.api.llm.map_search`).
4. The LLM API emits a signal to the LLM generate worker for processing.

## Future Work
- Implement actual LLM/geocoding logic for map search in the LLM agent.
