import os
from typing import Optional
import requests_cache
from retry_requests import retry
import openmeteo_requests
from openmeteo_sdk.VariablesWithTime import VariablesWithTime

from airunner_services.downloads.policy import (
    is_openmeteo_allowed,
)


class WeatherMixin:
    """Add Open-Meteo weather lookup to an agent manager."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def weather_cache_expiration(self) -> int:
        """Return the weather response cache lifetime in seconds."""
        return 3600

    @property
    def cache_path(self) -> str:
        """Return the local weather cache directory path."""
        return os.path.expanduser(
            os.path.join(
                self.path_settings.base_path,
                "text",
                "other",
                "cache",
                ".requests_cache",
            )
        )

    @property
    def unit_system(self) -> str:
        """Return the configured unit system."""
        return self.user.unit_system

    @property
    def is_metric(self) -> bool:
        """Return whether the configured unit system is metric."""
        return self.unit_system == "metric"

    @property
    def temperature_unit(self) -> str:
        """Return the temperature unit matching the unit system."""
        if self.is_metric:
            return "celsius"
        else:
            return "fahrenheit"

    @property
    def wind_speed_unit(self) -> str:
        """Return the wind speed unit matching the unit system."""
        if self.is_metric:
            return "km/h"
        else:
            return "mph"

    @property
    def precipitation_unit(self) -> str:
        """Return the precipitation unit matching the unit system."""
        if self.is_metric:
            return "mm"
        else:
            return "inch"

    @property
    def forecast_days(self) -> int:
        """Return the number of forecast days to request."""
        return 1

    @property
    def weather_prompt(self) -> str:
        """Return a prompt fragment describing current weather."""
        weather = self.get_weather()
        if not weather:
            return ""
        current_temperature_2m = weather.Variables(0).Value()
        current_precipitation = weather.Variables(1).Value()
        current_rain = weather.Variables(2).Value()
        current_showers = weather.Variables(3).Value()
        current_snowfall = weather.Variables(4).Value()
        current_wind_speed_10m = weather.Variables(5).Value()
        current_wind_direction_10m = weather.Variables(6).Value()
        current_wind_gusts_10m = weather.Variables(7).Value()
        return (
            "Current weather information:\n"
            f"- temperature: {current_temperature_2m} {self.temperature_unit}\n"
            f"- precipitation {current_precipitation} {self.precipitation_unit}\n"
            f"- rain {current_rain} {self.precipitation_unit}\n"
            f"- showers {current_showers} {self.precipitation_unit}\n"
            f"- snowfall {current_snowfall} {self.precipitation_unit}\n"
            f"- wind speed: {current_wind_speed_10m} {self.wind_speed_unit}\n"
            f"- wind direction: {current_wind_direction_10m}\n"
            f"- wind gusts: {current_wind_gusts_10m} {self.wind_speed_unit}\n"
        )

    def get_weather(self) -> Optional[VariablesWithTime]:
        """Fetch current weather variables when weather prompts are enabled."""
        if not is_openmeteo_allowed():
            return None
            
        if (
            not self.user.latitude
            or not self.user.longitude
            or not self.chatbot.use_weather_prompt
            or not self.llm_settings.use_weather_prompt
        ):
            return None

        cache_session = requests_cache.CachedSession(
            self.cache_path, expire_after=self.weather_cache_expiration
        )
        retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
        openmeteo = openmeteo_requests.Client(session=retry_session)
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": self.user.latitude,
            "longitude": self.user.longitude,
            "current": [
                "temperature_2m",
                "precipitation",
                "rain",
                "showers",
                "snowfall",
                "wind_speed_10m",
                "wind_direction_10m",
                "wind_gusts_10m",
            ],
            "temperature_unit": self.temperature_unit,
            "wind_speed_unit": self.wind_speed_unit,
            "precipitation_unit": self.precipitation_unit,
            "forecast_days": self.forecast_days,
        }
        responses = openmeteo.weather_api(url, params=params)
        try:
            response = responses[0]
            return response.Current()
        except IndexError as e:
            self.logger.error("Error getting weather: " + str(e))
            return None
