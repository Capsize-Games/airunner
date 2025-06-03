import re
from airunner.vendor.openvoice.text.english import (
    english_to_ipa2,
)
from airunner.vendor.openvoice.text.mandarin import (
    chinese_to_ipa,
)


def cjke_cleaners2(text):
    text = re.sub(
        r"\[ZH\](.*?)\[ZH\]", lambda x: chinese_to_ipa(x.group(1)) + " ", text
    )
    text = re.sub(
        r"\[JA\](.*?)\[JA\]",
        lambda x: japanese_to_ipa2(x.group(1)) + " ",
        text,
    )
    text = re.sub(
        r"\[KO\](.*?)\[KO\]", lambda x: korean_to_ipa(x.group(1)) + " ", text
    )
    text = re.sub(
        r"\[EN\](.*?)\[EN\]", lambda x: english_to_ipa2(x.group(1)) + " ", text
    )
    text = re.sub(r"\s+$", "", text)
    text = re.sub(r"([^\.,!\?\-…~])$", r"\1.", text)
    return text
