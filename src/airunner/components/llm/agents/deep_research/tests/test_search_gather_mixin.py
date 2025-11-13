import json
from datetime import datetime

import pytest

from airunner.components.llm.agents.deep_research.mixins.search_gather_mixin import (
    SearchGatherMixin,
)
from airunner.components.llm.agents.deep_research.mixins.content_validation_mixin import (
    ContentValidationMixin,
)
from airunner.components.tools.web_content_extractor import WebContentExtractor


class Dummy(SearchGatherMixin, ContentValidationMixin):
    def __init__(self):
        # minimal model stub will be attached as needed
        self._base_model = None


def test_fetch_meta_map_for_urls(monkeypatch):
    agent = Dummy()
    items = [{"link": "https://a.com"}]

    def fake_extract_with_links(url):
        return {"links": [{"url": "https://b.com"}], "content": "Hello world"}

    monkeypatch.setattr(
        WebContentExtractor,
        "extract_with_links",
        staticmethod(fake_extract_with_links),
    )
    meta_map = agent._fetch_meta_map_for_urls(items)
    assert "https://a.com" in meta_map
    assert meta_map["https://a.com"]["content"] == "Hello world"


def test_compute_adjustment_for_url_cross_and_age(monkeypatch):
    agent = Dummy()
    url = "https://a.com"
    url_set = {"https://a.com", "https://b.com"}
    # content born in 1984
    content = "This person was born in 1984"
    meta_map = {url: {"links": [{"url": "https://b.com"}], "content": content}}

    # Case 1: no profile, subject type unknown
    adjust_unknown = agent._compute_adjustment_for_url(
        url, url_set, meta_map, "unknown", None
    )
    assert pytest.approx(adjust_unknown, abs=1e-6) == 0.1

    # Case 2: person subject, profile age matching page age
    profile_age = datetime.now().year - 1984
    person_profile = {"approximate_age": profile_age}
    adjust_person = agent._compute_adjustment_for_url(
        url, url_set, meta_map, "person", person_profile
    )
    # With cross_score 1.0 and age_score 1.0, expected adjust: 0.25 + 0.25 = 0.5
    assert pytest.approx(adjust_person, abs=1e-6) == 0.5


def test_ask_llm_for_person_profile_parses_json():
    agent = Dummy()
    profile = {"name": "Joe", "approximate_age": 40}

    class FakeModel:
        def invoke(self, messages):
            return type("R", (), {"content": json.dumps(profile)})()

    agent._base_model = FakeModel()
    parsed = agent._ask_llm_for_person_profile(
        "Joe Example", "Some sample text"
    )
    assert parsed == profile
