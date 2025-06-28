# Maps

This component provides a map interface using Leaflet.js, allowing users to visualize and interact with geographical data.

## Setup

- [Download the latest leaflet release](https://github.com/Leaflet/Leaflet/releases/tag/v1.9.4)
- Unzip and extract the contents of the `dist` folder to `src/airunner/components/map/gui/static/leaflet`

## Nominatim Server Integration

You can configure the map component to use a custom Nominatim server for geocoding and reverse geocoding by setting the `AIRUNNER_NOMINATIM_URL` environment variable. For example, to use a local Nominatim server running on port 8080:

```bash
export AIRUNNER_NOMINATIM_URL="http://localhost:8080/"
```

If this variable is not set, the map will use the default OpenStreetMap Nominatim service.