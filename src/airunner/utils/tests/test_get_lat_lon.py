"""
Unit tests for airunner.utils.location.get_lat_lon.get_lat_lon
"""

import pytest
from unittest.mock import patch


def test_get_lat_lon_success(monkeypatch):
    mock_response = type(
        "Resp",
        (),
        {
            "json": lambda self: [
                {"lat": "1.23", "lon": "4.56", "display_name": "Test Place"}
            ]
        },
    )()
    monkeypatch.setattr("requests.request", lambda *a, **k: mock_response)
    from airunner.utils.location.get_lat_lon import get_lat_lon

    result = get_lat_lon("90210", "US")
    assert result == (1.23, 4.56, "Test Place")


def test_get_lat_lon_none(monkeypatch):
    mock_response = type("Resp", (), {"json": lambda self: []})()
    monkeypatch.setattr("requests.request", lambda *a, **k: mock_response)
    from airunner.utils.location.get_lat_lon import get_lat_lon

    result = get_lat_lon("00000", "US")
    assert result is None
