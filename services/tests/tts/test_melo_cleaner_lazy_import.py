"""Regression tests for optional Melo language imports."""

from airunner.enums import AvailableLanguage
from airunner_services.vendor.melo.text.cleaner import Cleaner


def test_cleaner_initializes_without_optional_japanese_dependencies():
    cleaner = Cleaner()

    assert cleaner.language is AvailableLanguage.EN
    assert AvailableLanguage.JP in cleaner.language_module_map