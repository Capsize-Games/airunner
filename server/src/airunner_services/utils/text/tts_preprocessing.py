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


# Non-overlapping Unicode ranges for emoji characters.
# Defined as a module-level constant so the regex is compiled once.
_EMOJI_RANGES: list[tuple[int, int]] = [
    (0x1F600, 0x1F64F),  # Emoticons
    (0x1F300, 0x1F5FF),  # Misc Symbols and Pictographs
    (0x1F680, 0x1F6FF),  # Transport and Map Symbols
    (0x1F700, 0x1F77F),  # Alchemical Symbols
    (0x1F780, 0x1F7FF),  # Geometric Shapes Extended
    (0x1F800, 0x1F8FF),  # Supplemental Arrows-C
    (0x1F900, 0x1F9FF),  # Supplemental Symbols and Pictographs
    (0x1FA00, 0x1FA6F),  # Chess Symbols
    (0x1FA70, 0x1FAFF),  # Symbols and Pictographs Extended-A
    (0x2702, 0x27B0),  # Dingbats
    (0x24C2, 0x24C2),  # Ⓜ metro
    (0x25B6, 0x25B6),  # ▶ play button
    (0x25C0, 0x25C0),  # ◀ reverse button
    (0x25FB, 0x25FE),  # ◻◼◽◾ medium squares
    (0x2600, 0x26FF),  # Miscellaneous Symbols
    (0x2B05, 0x2B55),  # ⬅⬆⬇ arrows, stars
    (0x1F100, 0x1F1FF),  # Enclosed Alphanumeric Supplement
    (0x1F200, 0x1F2FF),  # Enclosed Ideographic Supplement
]

_EMOJI_PATTERN = re.compile(
    "[" + "".join(f"{chr(lo)}-{chr(hi)}" for lo, hi in _EMOJI_RANGES) + "]+",
    flags=re.UNICODE,
)


def strip_emoji_characters(text: str) -> str:
    """Remove emoji code points before sending text to TTS."""
    return _EMOJI_PATTERN.sub("", text)


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
