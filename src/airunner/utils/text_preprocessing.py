"""
Utility functions for preprocessing text before speech synthesis.
"""
import re
import inflect


def prepare_text_for_tts(text: str) -> str:
    """
    Prepare text for text-to-speech processing by replacing characters,
    removing emojis, and converting numbers to words.
    
    Args:
        text: The input text to preprocess
        
    Returns:
        Preprocessed text suitable for TTS
    """
    text = replace_unspeakable_characters(text)
    text = strip_emoji_characters(text)
    # Roman numeral conversion currently disabled because we need to distinguish
    # between "I" as a pronoun and "I" as a Roman numeral
    # text = roman_to_int(text)
    text = replace_numbers_with_words(text)
    text = replace_misc_with_words(text)
    return text


def replace_unspeakable_characters(text: str) -> str:
    """Replace characters that don't synthesize well in TTS."""
    # Replace ellipsis and other unspeakable characters
    text = text.replace("...", " ")
    text = text.replace("…", " ")
    text = text.replace("“", "")
    text = text.replace("”", "")
    text = text.replace("–", "")
    text = text.replace("—", "")
    text = text.replace('"', "")
    text = text.replace("-", "")
    text = text.replace("-", "")

    # Replace windows newlines
    text = text.replace("\r\n", " ")

    # Replace newlines
    text = text.replace("\n", " ")

    # Replace tabs
    text = text.replace("\t", " ")

    # Remove single quotes used as quotes but keep apostrophes
    text = re.sub(r"(?<=\W)'|'(?=\W)", "", text)
    text = re.sub(r"'|'", "", text)

    return text


def strip_emoji_characters(text: str) -> str:
    """Remove emoji characters from text."""
    # strip emojis
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F700-\U0001F77F"  # alchemical symbols
        "\U0001F780-\U0001F7FF"  # Geometric Shapes Extended
        "\U0001F800-\U0001F8FF"  # Supplemental Arrows-C
        "\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
        "\U0001FA00-\U0001FA6F"  # Chess Symbols
        "\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
        "\U00002702-\U000027B0"  # Dingbats
        "\U000024C2-\U0001F251"
        "]+", flags=re.UNICODE
    )
    text = emoji_pattern.sub(r'', text)
    return text


def replace_numbers_with_words(text: str) -> str:
    """Convert numeric digits to their word equivalents."""
    p = inflect.engine()

    # Handle time formats separately
    text = re.sub(r'(\d+):(\d+)([APap][Mm])', 
                lambda m: f"{p.number_to_words(m.group(1))} {p.number_to_words(m.group(2)).replace('zero', '').replace('-', ' ')} {m.group(3)[0].upper()} {m.group(3)[1].upper()}", 
                text)
    text = re.sub(r'(\d+):(\d+)', 
                lambda m: f"{p.number_to_words(m.group(1))} {p.number_to_words(m.group(2)).replace('-', ' ')}", 
                text)

    # Split text into words and non-word characters
    words = re.findall(r'\d+|\D+', text)

    for i in range(len(words)):
        if words[i].isdigit():  # check if the word is a digit
            words[i] = p.number_to_words(words[i]).replace('-', ' ')

    # Join words with a space to ensure proper spacing
    result = ' '.join(words).replace('  ', ' ')

    # Ensure "PM" and "AM" are correctly spaced
    result = re.sub(r'\b([AP])M\b', r'\1 M', result)

    return result


def replace_misc_with_words(text: str) -> str:
    """Replace miscellaneous symbols with their word equivalents."""
    text = text.replace("°F", "degrees Fahrenheit")
    text = text.replace("°C", "degrees Celsius")
    text = text.replace("°", "degrees")
    return text


def roman_to_int(text: str) -> str:
    """Convert Roman numerals to integers."""
    roman_numerals = {
        'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000
    }

    def convert_roman_to_int(roman):
        total = 0
        prev_value = 0
        for char in reversed(roman):
            value = roman_numerals[char]
            if value < prev_value:
                total -= value
            else:
                total += value
            prev_value = value
        return str(total)

    # Replace Roman numerals with their integer values
    result = re.sub(r'\b[IVXLCDM]+\b', lambda match: convert_roman_to_int(match.group(0)), text)
    return result
