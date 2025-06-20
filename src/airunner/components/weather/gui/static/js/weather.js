// Assumes WeatherAPI is loaded globally as window.weatherAPI_isReady
class WeatherAPI {
    constructor() {
    }
}

document.addEventListener('DOMContentLoaded', function () {
    window.weatherAPI = new WeatherAPI(map);
    window.weatherAPI_isReady = true;
    if (window.weatherAPI) {
        window.weatherAPI._triggerEvent('weather-ready');
    }
});