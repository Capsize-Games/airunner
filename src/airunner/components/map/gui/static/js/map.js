// map.js - Leaflet MapAPI with BrowserAPI integration

// Assumes BrowserAPI is loaded globally as window.browserAPI
class MapAPI {
    constructor(mapInstance) {
        this.map = mapInstance;
        this.markers = [];  // Changed to array to support multiple markers
    }

    addMarker(lat, lon, label = null) {
        const marker = L.marker([lat, lon]).addTo(this.map);
        if (label) {
            marker.bindPopup(label);
        }
        this.markers.push(marker);
        return `Marker added at ${lat}, ${lon}`;
    }

    clearMarkers() {
        this.markers.forEach(marker => {
            this.map.removeLayer(marker);
        });
        this.markers = [];
        return "All markers cleared";
    }

    moveMap(lat, lon, zoom = 13) {
        this.map.setView([lat, lon], zoom);
        return `Map moved to ${lat}, ${lon}`;
    }

    getMapDebugState() {
        return JSON.stringify({
            mapCenter: this.map ? this.map.getCenter() : null,
            mapZoom: this.map ? this.map.getZoom() : null,
            markerCount: this.markers.length,
            markerPositions: this.markers.map(m => m.getLatLng())
        });
    }
}

window.mapAPI = null;
window.mapAPI_isReady = false;

document.addEventListener('DOMContentLoaded', function () {
    const map = L.map('map', {
        attributionControl: false,
    }).setView([51.505, -0.09], 13);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);
    window.mapAPI = new MapAPI(map);
    window.mapAPI_isReady = true;
    if (window.browserAPI) {
        window.browserAPI._triggerEvent('map-ready');
    }
});

// Listen for commands from Python via BrowserAPI
function handleMapCommand(command, data) {
    if (!window.mapAPI) return;
    if (command === 'addMarker') {
        window.mapAPI.addMarker(data.lat, data.lon, data.label);
    } else if (command === 'moveMap') {
        window.mapAPI.moveMap(data.lat, data.lon, data.zoom);
    } else if (command === 'clearMarkers') {
        window.mapAPI.clearMarkers();
    }
}

if (window.browserAPI) {
    window.browserAPI.on('map-command', (payload) => {
        handleMapCommand(payload.command, payload.data);
    });
}
