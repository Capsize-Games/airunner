"""Service-owned helpers for preparing text for TTS synthesis."""

from __future__ import annotations

import re

import inflect


def prepare_text_for_tts(text: str) -> str:
    """Normalize text into a form that synthesizes cleanly."""
    text = replace_unspeakable_characters(text)
    text = strip_emoji_characters(text)
    text = replace_numbers_with_words(text)
    text = replace_misc_with_words(text)
    return text


def replace_unspeakable_characters(text: str) -> str:
    """Replace punctuation and whitespace that degrade TTS output."""
    text = text.replace("...", " ")
    text = text.replace("…", " ")
    text = text.replace("“", "")
    text = text.replace("”", "")
    text = text.replace("–", "")
    text = text.replace("—", "")
    text = text.replace('"', "")
    text = text.replace("-", "")
    text = text.replace("\r\n", " ")
    text = text.replace("\n", " ")
    text = text.replace("\t", " ")
    text = re.sub(r"(?<=\W)'|'(?=\W)", "", text)
    text = re.sub(r"'|'", "", text)
    return text


def strip_emoji_characters(text: str) -> str:
    """Remove emoji code points before sending text to TTS."""
    emoji_pattern = re.compile(
        "["
        "\U0001f600-\U0001f64f"  # Emoticons
        "\U0001f300-\U0001f5ff"  # Misc Symbols and Pictographs
        "\U0001f680-\U0001f6ff"  # Transport and Map Symbols
        "\U0001f700-\U0001f77f"  # Alchemical Symbols
        "\U0001f780-\U0001f7ff"  # Geometric Shapes Extended
        "\U0001f800-\U0001f8ff"  # Supplemental Arrows-C
        "\U0001f900-\U0001f9ff"  # Supplemental Symbols and Pictographs
        "\U0001fa00-\U0001fa6f"  # Chess Symbols
        "\U0001fa70-\U0001faff"  # Symbols and Pictographs Extended-A
        "\U00002702-\U000027b0"  # Dingbats
        "\U000024c2"             # Ⓜ metro
        "\U000025b6"             # ▶ play button
        "\U000025c0"             # ◀ reverse button
        "\U000025fb-\U000025fe"  # ◻◼◽◾ medium squares
        "\U00002600-\U000026ff"  # Miscellaneous Symbols
        "\U000026bd-\U000026be"  # ⚽⚾ sports
        "\U00002b05-\U00002b55"  # ⬅⬆⬇ arrows, stars
        "\U0001f100-\U0001f1ff"  # Enclosed Alphanumeric Supplement
        "\U0001f200-\U0001f2ff"  # Enclosed Ideographic Supplement
        "]+",
        flags=re.UNICODE,
    )
    return emoji_pattern.sub("", text)


def replace_numbers_with_words(text: str) -> str:
    """Convert numeric text into a more speakable word form."""
    engine = inflect.engine()

    def format_time_with_meridiem(match: re.Match[str]) -> str:
        minutes = engine.number_to_words(match.group(2))
        minutes = minutes.replace("zero", "")
        minutes = minutes.replace("-", " ")
        meridiem = match.group(3)
        return (
            f"{engine.number_to_words(match.group(1))} {minutes} "
            f"{meridiem[0].upper()} {meridiem[1].upper()}"
        )

    def format_time(match: re.Match[str]) -> str:
        minutes = engine.number_to_words(match.group(2))
        minutes = minutes.replace("-", " ")
        return f"{engine.number_to_words(match.group(1))} {minutes}"

    text = re.sub(
        r"(\d+):(\d+)([APap][Mm])",
        format_time_with_meridiem,
        text,
    )
    text = re.sub(
        r"(\d+):(\d+)",
        format_time,
        text,
    )
    words = re.findall(r"\d+|\D+", text)
    for index, word in enumerate(words):
        if word.isdigit():
            words[index] = engine.number_to_words(word).replace("-", " ")
    result = " ".join(words).replace("  ", " ")
    return re.sub(r"\b([AP])M\b", r"\1 M", result)


def replace_misc_with_words(text: str) -> str:
    """Expand common symbols into words that TTS can pronounce."""
    text = text.replace("°F", "degrees Fahrenheit")
    text = text.replace("°C", "degrees Celsius")
    text = text.replace("°", "degrees")
    return text


def roman_to_int(text: str) -> str:
    """Convert Roman numeral tokens to integers."""
    roman_numerals = {
        "I": 1,
        "V": 5,
        "X": 10,
        "L": 50,
        "C": 100,
        "D": 500,
        "M": 1000,
    }

    def convert_roman_to_int(roman: str) -> str:
        total = 0
        previous_value = 0
        for char in reversed(roman):
            value = roman_numerals[char]
            if value < previous_value:
                total -= value
            else:
                total += value
            previous_value = value
        return str(total)

    return re.sub(
        r"\b[IVXLCDM]+\b",
        lambda match: convert_roman_to_int(match.group(0)),
        text,
    )


__all__ = [
    "prepare_text_for_tts",
    "replace_misc_with_words",
    "replace_numbers_with_words",
    "replace_unspeakable_characters",
    "roman_to_int",
    "strip_emoji_characters",
]
