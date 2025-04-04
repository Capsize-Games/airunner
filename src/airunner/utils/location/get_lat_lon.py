from typing import Tuple, Optional, Any
import requests


def get_lat_lon(
    zipcode: str, 
    country_code: str = "US"
) -> Optional[Tuple[float, float, Any]]:
    url = f"https://nominatim.openstreetmap.org/search?postalcode={zipcode}&country={country_code}&format=json"
    payload = {}
    headers = {
        "User-Agent": "AI Runner/1.0 (capsizegames@fastmail.com)"
    }

    response = requests.request("GET", url, headers=headers, data=payload)
    data = response.json()
    
    if data:
        lat = data[0]["lat"]
        lon = data[0]["lon"]
        display_name = data[0]["display_name"]
        return float(lat), float(lon), display_name
    else:
        return None
