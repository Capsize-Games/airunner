from datetime import datetime

from airunner.components.llm.agents.deep_research.mixins.content_validation_mixin import (
    ContentValidationMixin,
)


class Dummy(ContentValidationMixin):
    pass


def test_extract_approximate_age_from_year_of_birth():
    dummy = Dummy()
    base_year = 1984
    text = f"This person was born in {base_year}."
    expected = datetime.now().year - base_year
    assert dummy._extract_approximate_age_from_text(text) == expected


def test_extract_approximate_age_from_age_phrase():
    dummy = Dummy()
    text = "John Doe, a 60-year-old citizen in the city."
    assert dummy._extract_approximate_age_from_text(text) == 60


def test_extract_approximate_age_none_for_no_age():
    dummy = Dummy()
    text = "No age info here."
    assert dummy._extract_approximate_age_from_text(text) is None
