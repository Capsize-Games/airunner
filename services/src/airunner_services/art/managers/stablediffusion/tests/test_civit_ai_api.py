import requests
import pytest

from airunner.components.art.managers.stablediffusion.civit_ai_api import (
    CivitAIAPI,
)


def test_parse_url_with_version():
    url = "https://civitai.com/models/995002/70s-sci-fi-movie?modelVersionId=1880417"
    ids = CivitAIAPI.parse_url(url)
    assert ids["model_id"] == "995002"
    assert ids["model_version_id"] == "1880417"


def test_parse_url_no_version():
    url = "https://civitai.com/models/12345/some-model"
    ids = CivitAIAPI.parse_url(url)
    assert ids["model_id"] == "12345"
    assert ids["model_version_id"] is None


def test_get_model_info_invalid_url_raises(monkeypatch):
    api = CivitAIAPI()
    monkeypatch.setattr(
        CivitAIAPI,
        "parse_url",
        lambda self, u: {"model_id": None, "model_version_id": None},
    )
    with pytest.raises(ValueError):
        api.get_model_info("invalid")


class DummyResp:
    def __init__(self, data):
        self._data = data

    def raise_for_status(self):
        return None

    def json(self):
        return self._data


def test_get_model_info_selects_version(monkeypatch):
    api = CivitAIAPI(api_key="KEY")
    monkeypatch.setattr(
        CivitAIAPI,
        "parse_url",
        lambda self, u: {"model_id": "1", "model_version_id": "2"},
    )

    data = {"modelVersions": [{"id": 2, "name": "v2"}, {"id": 3}]}

    def fake_get(url, headers, timeout):
        assert "token=KEY" in url
        return DummyResp(data)

    monkeypatch.setattr(requests, "get", fake_get)
    res = api.get_model_info("https://civitai.com/models/1?modelVersionId=2")
    assert res.get("selectedVersion", {}).get("id") == 2
