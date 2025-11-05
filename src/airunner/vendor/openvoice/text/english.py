"""from https://github.com/keithito/tacotron"""

"""
Cleaners are transformations that run over the input text at both training and eval time.

Cleaners can be selected by passing a comma-delimited list of cleaner names as the "cleaners"
hyperparameter. Some cleaners are English-specific. You'll typically want to use:
  1. "english_cleaners" for English text
  2. "transliteration_cleaners" for non-English text that can be transliterated to ASCII using
     the Unidecode library (https://pypi.python.org/pypi/Unidecode)
  3. "basic_cleaners" if you do not want to transliterate (in this case, you should also update
     the symbols in symbols.py to match your data).
"""


# Regular expression matching whitespace:


import re
import inflect
from unidecode import unidecode
import eng_to_ipa as ipa

_inflect = inflect.engine()
_comma_number_re = re.compile(r"([0-9][0-9\,]+[0-9])")
_decimal_number_re = re.compile(r"([0-9]+\.[0-9]+)")
_pounds_re = re.compile(r"£([0-9\,]*[0-9]+)")
_dollars_re = re.compile(r"\$([0-9]+(?:\.[0-9]+)?)")
_ordinal_re = re.compile(r"([0-9]+)(st|nd|rd|th)")
# Captures number and suffix separately
_number_re = re.compile(r"[0-9]+")

# List of (regular expression, replacement) pairs for abbreviations:
_abbreviations = [
    (re.compile(r"\b" + re.escape(x[0]) + r"\.", re.IGNORECASE), x[1])
    for x in [
        ("mrs", "misess"),
        ("mr", "mister"),
        ("dr", "doctor"),
        ("st", "saint"),
        ("co", "company"),
        ("jr", "junior"),
        ("maj", "major"),
        ("gen", "general"),
        ("drs", "doctors"),
        ("rev", "reverend"),
        ("lt", "lieutenant"),
        ("hon", "honorable"),
        ("sgt", "sergeant"),
        ("capt", "captain"),
        ("esq", "esquire"),
        ("ltd", "limited"),
        ("col", "colonel"),
        ("ft", "fort"),
    ]
]


# List of (ipa, lazy ipa) pairs:
_lazy_ipa = [
    (re.compile("%s" % x[0]), x[1])
    for x in [
        ("r", "ɹ"),
        ("æ", "e"),
        ("ɑ", "a"),
        ("ɔ", "o"),
        ("ð", "z"),
        ("θ", "s"),
        ("ɛ", "e"),
        ("ɪ", "i"),
        ("ʊ", "u"),
        ("ʒ", "ʥ"),
        ("ʤ", "ʥ"),
        ("ˈ", "↓"),
    ]
]

# List of (ipa, lazy ipa2) pairs:
_lazy_ipa2 = [
    (re.compile("%s" % x[0]), x[1])
    for x in [
        ("r", "ɹ"),
        ("ð", "z"),
        ("θ", "s"),
        ("ʒ", "ʑ"),
        ("ʤ", "dʑ"),
        ("ˈ", "↓"),
    ]
]

# List of (ipa, ipa2) pairs
_ipa_to_ipa2 = [
    (re.compile("%s" % x[0]), x[1])
    for x in [("r", "ɹ"), ("ʤ", "dʒ"), ("ʧ", "tʃ")]
]


def expand_abbreviations(text):
    for regex, replacement in _abbreviations:
        text = re.sub(regex, replacement, text)
    return text


def collapse_whitespace(text):
    return re.sub(r"\s+", " ", text)


def _remove_commas(m):
    return m.group(1).replace(",", "")


def _expand_decimal_point(m):
    integer, decimal = m.group(1).split(".")
    return f"{integer} point {decimal}"


def _expand_dollars(m):
    match = m.group(1)
    parts = match.split(".")
    if len(parts) > 2:
        return match + " dollars"  # Unexpected format
    dollars = int(parts[0]) if parts[0] else 0
    cents = int(parts[1]) if len(parts) > 1 and parts[1] else 0
    if dollars and cents:
        dollar_unit = "dollar" if dollars == 1 else "dollars"
        cent_unit = "cent" if cents == 1 else "cents"
        return f"{dollars} {dollar_unit}, {cents} {cent_unit}"
    elif dollars:
        dollar_unit = "dollar" if dollars == 1 else "dollars"
        return f"{dollars} {dollar_unit}"
    elif cents:
        cent_unit = "cent" if cents == 1 else "cents"
        return f"{cents} {cent_unit}"
    else:
        return "zero dollars"


def _expand_pounds(m):
    num_str = m.group(1).replace(",", "")  # Remove commas from pound amount
    num = int(num_str)
    return f"{num} {'pound' if num == 1 else 'pounds'}"


def _expand_ordinal(m):
    num_str = m.group(1)  # This is the number part, e.g., "21" from "21st"
    # First get ordinal string (e.g., "21st"), then convert to words ("twenty-first")
    return _inflect.number_to_words(_inflect.ordinal(num_str))


def _expand_number(m):
    num = int(m.group(0))
    s_num = m.group(0)  # string form, useful for 'oh' in years like 1907

    # Default expansion using inflect
    expanded_num = _inflect.number_to_words(num, andword="").replace(",", "")

    # Specific year pronunciations overrides
    # Handles 19xx years
    if 1900 <= num <= 1999:
        if num % 100 == 0:  # e.g., 1900
            return (
                _inflect.number_to_words(num // 100, andword="") + " hundred"
            )  # "nineteen hundred"
        else:  # e.g., 1901, 1984
            part1 = _inflect.number_to_words(
                num // 100, andword=""
            )  # "nineteen"
            part2_val = num % 100
            if (
                s_num[2] == "0"
            ):  # Handles "oh" for years like 1907 ("nineteen oh seven")
                part2 = "oh " + _inflect.number_to_words(part2_val, andword="")
            else:  # Handles years like 1984 ("nineteen eighty-four")
                part2 = _inflect.number_to_words(part2_val, andword="")
            return f"{part1} {part2}"
    # Handles 2000
    elif num == 2000:
        return "two thousand"
    # Handles 200x years (e.g., 2001-2009)
    elif 2000 < num < 2010:
        return "two thousand " + _inflect.number_to_words(
            num % 100, andword=""
        )  # "two thousand one"

    # For other numbers (e.g., 1234) or years where standard expansion is preferred (e.g., 2024),
    # the default 'expanded_num' (e.g. "one thousand two hundred thirty-four", "two thousand twenty-four") is returned.
    return expanded_num


def normalize_numbers(text):
    placeholders = {}
    placeholder_idx = 0

    def idx_to_alpha(idx):
        # Convert 0 -> A, 1 -> B, ..., 25 -> Z, 26 -> AA, etc.
        s = ""
        while True:
            s = chr(ord("A") + (idx % 26)) + s
            idx = idx // 26 - 1
            if idx < 0:
                break
        return s

    def add_placeholder(value_func, match_obj):
        nonlocal placeholder_idx
        key = f"PHPLACEHOLDER_{idx_to_alpha(placeholder_idx)}"
        placeholders[key] = value_func(match_obj)
        placeholder_idx += 1
        return key

    # 1. Remove commas from multi-digit numbers (e.g., "1,234" -> "1234")
    text = re.sub(_comma_number_re, _remove_commas, text)

    # 2. Process and placeholder pounds. Uses _expand_pounds.
    text = re.sub(
        _pounds_re, lambda m: add_placeholder(_expand_pounds, m), text
    )

    # 3. Process and placeholder dollars. Uses _expand_dollars.
    text = re.sub(
        _dollars_re, lambda m: add_placeholder(_expand_dollars, m), text
    )

    # 4. Process and placeholder decimals. Uses _expand_decimal_point.
    text = re.sub(
        _decimal_number_re,
        lambda m: add_placeholder(_expand_decimal_point, m),
        text,
    )

    # 5. Process and placeholder ordinals. Uses _expand_ordinal.
    text = re.sub(
        _ordinal_re, lambda m: add_placeholder(_expand_ordinal, m), text
    )

    # 6. Expand remaining numbers to words. Uses _expand_number.
    # These are numbers that weren't part of currency, decimals, or ordinals.
    text = re.sub(
        _number_re, lambda m: add_placeholder(_expand_number, m), text
    )

    # 7. Restore placeholders in the correct order.
    for key in sorted(placeholders.keys(), key=len, reverse=True):
        text = text.replace(key, placeholders[key])

    return text


def mark_dark_l(text):
    return re.sub(
        r"l([^aeiouæɑɔəɛɪʊ ]*(?: |$))", lambda x: "ɫ" + x.group(1), text
    )


def english_to_ipa(text):
    text = unidecode(text).lower()
    text = expand_abbreviations(text)
    text = normalize_numbers(text)
    phonemes = ipa.convert(text)
    phonemes = collapse_whitespace(phonemes)
    return phonemes


def english_to_lazy_ipa(text):
    text = english_to_ipa(text)
    for regex, replacement in _lazy_ipa:
        text = re.sub(regex, replacement, text)
    return text


def english_to_ipa2(text):
    text = english_to_ipa(text)
    text = mark_dark_l(text)
    for regex, replacement in _ipa_to_ipa2:
        text = re.sub(regex, replacement, text)
    return text.replace("...", "…")


def english_to_lazy_ipa2(text):
    text = english_to_ipa(text)
    for regex, replacement in _lazy_ipa2:
        text = re.sub(regex, replacement, text)
    return text
