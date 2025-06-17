# Map Widget Module

This module provides a Qt widget for displaying and interacting with a Leaflet.js map inside a QWebEngineView, with robust two-way communication between Python and JavaScript using a WebChannel and a generic BrowserAPI.

## Key Components

- **map_widget.py**: Python widget class. Exposes `add_marker(lat, lon)` and `center_map(lat, lon, zoom=13)` methods for map control.
- **map.jinja2.html**: HTML template for the map. Loads static CSS/JS and the BrowserAPI for communication.
- **map.js**: JavaScript file. Implements a `MapAPI` class and listens for commands from Python via the BrowserAPI.
- **map.css**: CSS file for map styling.

## Usage

1. **Python API**
   - Call `add_marker(lat, lon)` to add a marker at the specified coordinates.
   - Call `center_map(lat, lon, zoom=13)` to center the map.
   - These methods can be triggered from signals or other code.

2. **Communication**
   - Uses the same BrowserAPI (`api.js`) as the game/browser widgets for robust JS-Python messaging.
   - All JS and CSS are loaded as static files; no inline code in the HTML.

## Extending
- To add more map features, extend the `MapAPI` class in `map.js` and add corresponding Python methods in `MapWidget`.

## Example

```python
widget = MapWidget()
widget.center_map(40.7128, -74.0060, zoom=12)
widget.add_marker(40.7128, -74.0060)
```

## See Also
- [Browser Widget API Documentation](../../browser/gui/static/js/api.js)
- [Leaflet.js Documentation](https://leafletjs.com/)
