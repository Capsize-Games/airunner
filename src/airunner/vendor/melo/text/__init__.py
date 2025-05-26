from airunner.enums import AvailableLanguage
from airunner.vendor.melo.text.symbols import *


_symbol_to_id = {s: i for i, s in enumerate(symbols)}
from airunner.vendor.melo.text import language_tone_start_map


def cleaned_text_to_sequence(
    cleaned_text,
    tones,
    language: AvailableLanguage = AvailableLanguage.EN,
    symbol_to_id=None,
):
    """Converts a string of text to a sequence of IDs corresponding to the symbols in the text.
    Args:
      text: string to convert to a sequence
    Returns:
      List of integers corresponding to the symbols in the text
    """
    symbol_to_id_map = symbol_to_id if symbol_to_id else _symbol_to_id
    phones = [symbol_to_id_map[symbol] for symbol in cleaned_text]
    if language not in language_tone_start_map:
        tone_start = language_tone_start_map[AvailableLanguage.EN]
        lang_id = language_id_map[AvailableLanguage.EN]
    else:
        tone_start = language_tone_start_map[language]
        lang_id = language_id_map[language]
    tones = [i + tone_start for i in tones]
    lang_ids = [lang_id for i in phones]
    return phones, tones, lang_ids


def get_bert(*args, **kwargs):
    """Stub for get_bert to satisfy imports in data_utils.py during testing."""
    raise NotImplementedError("get_bert is not implemented in this stub.")
