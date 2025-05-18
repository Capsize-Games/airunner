# Convert Japanese text to phonemes which is
# compatible with Julius https://github.com/julius-speech/segmentation-kit
import re
import unicodedata

from transformers import AutoTokenizer
from airunner.vendor.melo.text import symbols
import pdb
from pykakasi import kakasi
from airunner.vendor.melo.text import japanese_bert
from airunner.vendor.melo.text.japanese_bert import get_bert_feature
from num2words import num2words
from airunner.api import API
from airunner.vendor.melo.text.japanese_settings import (
    punctuation,
    _CONVRULES,
    _ALPHASYMBOL_YOMI,
    _NUMBER_WITH_SEPARATOR_RX,
    _CURRENCY_MAP,
    _CURRENCY_RX,
    _NUMBER_RX,
    _HIRA2KATATRANS,
    _SYMBOL_TOKENS,
    _NO_YOMI_TOKENS,
    rep_map,
)

try:
    import MeCab

    try:
        import unidic_lite

        _DICDIR = unidic_lite.DICDIR
    except ImportError:
        import unidic

        _DICDIR = unidic.DICDIR
except ImportError as e:
    raise ImportError(
        "Japanese requires mecab-python3 and unidic-lite or unidic."
    ) from e


def _makerulemap():
    l = [tuple(x.split("/")) for x in _CONVRULES]
    return tuple({k: v for k, v in l if len(k) == i} for i in (1, 2))


_RULEMAP1, _RULEMAP2 = _makerulemap()


def kata2phoneme(text: str) -> str:
    """Convert katakana text to phonemes."""
    text = text.strip()
    res = []
    while text:
        if len(text) >= 2:
            x = _RULEMAP2.get(text[:2])
            if x is not None:
                text = text[2:]
                res += x.split(" ")[1:]
                continue
        x = _RULEMAP1.get(text[0])
        if x is not None:
            text = text[1:]
            res += x.split(" ")[1:]
            continue
        res.append(text[0])
        text = text[1:]
    # res = _COLON_RX.sub(":", res)
    return res


def hira2kata(text: str) -> str:
    text = text.translate(_HIRA2KATATRANS)
    return text.replace("う゛", "ヴ")


def get_tagger():
    import MeCab

    try:
        import unidic_lite

        dicdir = unidic_lite.DICDIR
    except ImportError:
        import unidic

        dicdir = unidic.DICDIR
    # Check if mecabrc exists in the dictionary directory
    import os

    mecabrc_path = os.path.join(dicdir, "mecabrc")
    if not os.path.isfile(mecabrc_path):
        raise RuntimeError(
            f"MeCab dictionary directory '{dicdir}' is missing mecabrc. Please ensure unidic or unidic-lite is installed and extracted correctly. (Looked for: {mecabrc_path})"
        )
    return MeCab.Tagger(f"-d {dicdir}")


# Use lazy initialization for the tagger to avoid import-time errors
_TAGGER = None


def text2kata(text: str) -> str:
    global _TAGGER
    if _TAGGER is None:
        _TAGGER = get_tagger()
    parsed = _TAGGER.parse(text)
    res = []
    for line in parsed.split("\n"):
        if line == "EOS":
            break
        parts = line.split("\t")

        word, yomi = parts[0], parts[1]
        if yomi:
            try:
                res.append(yomi.split(",")[6])
            except:
                pdb.set_trace()
        else:
            if word in _SYMBOL_TOKENS:
                res.append(word)
            elif word in ("っ", "ッ"):
                res.append("ッ")
            elif word in _NO_YOMI_TOKENS:
                pass
            else:
                res.append(word)
    return hira2kata("".join(res))


def japanese_convert_numbers_to_words(text: str) -> str:
    res = _NUMBER_WITH_SEPARATOR_RX.sub(lambda m: m[0].replace(",", ""), text)
    res = _CURRENCY_RX.sub(lambda m: m[2] + _CURRENCY_MAP.get(m[1], m[1]), res)
    res = _NUMBER_RX.sub(lambda m: num2words(m[0], lang="ja"), res)
    return res


def japanese_convert_alpha_symbols_to_words(text: str) -> str:
    return "".join([_ALPHASYMBOL_YOMI.get(ch, ch) for ch in text.lower()])


def japanese_text_to_phonemes(text: str) -> str:
    """Convert Japanese text to phonemes."""
    res = unicodedata.normalize("NFKC", text)
    res = japanese_convert_numbers_to_words(res)
    res = japanese_convert_alpha_symbols_to_words(res)
    res = text2kata(res)
    res = kata2phoneme(res)
    return res


def is_japanese_character(char):
    # 定义日语文字系统的 Unicode 范围
    japanese_ranges = [
        (0x3040, 0x309F),  # 平假名
        (0x30A0, 0x30FF),  # 片假名
        (0x4E00, 0x9FFF),  # 汉字 (CJK Unified Ideographs)
        (0x3400, 0x4DBF),  # 汉字扩展 A
        (0x20000, 0x2A6DF),  # 汉字扩展 B
        # 可以根据需要添加其他汉字扩展范围
    ]

    # 将字符的 Unicode 编码转换为整数
    char_code = ord(char)

    # 检查字符是否在任何一个日语范围内
    for start, end in japanese_ranges:
        if start <= char_code <= end:
            return True

    return False


def replace_punctuation(text):
    pattern = re.compile("|".join(re.escape(p) for p in rep_map.keys()))

    replaced_text = pattern.sub(lambda x: rep_map[x.group()], text)

    replaced_text = re.sub(
        r"[^\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF\u3400-\u4DBF"
        + "".join(punctuation)
        + r"]+",
        "",
        replaced_text,
    )

    return replaced_text


# Initialize kakasi object
kakasi = kakasi()
# Set options for converting Chinese characters to Katakana
kakasi.setMode("J", "K")  # Chinese to Katakana
kakasi.setMode("H", "K")  # Hiragana to Katakana
# Convert Chinese characters to Katakana
conv = kakasi.getConverter()
model_id = API().paths["tohoku-nlp/bert-base-japanese-v3"]
tokenizer = AutoTokenizer.from_pretrained(model_id)


def text_normalize(text):
    res = unicodedata.normalize("NFKC", text)
    res = japanese_convert_numbers_to_words(res)
    res = "".join([i for i in res if is_japanese_character(i)])
    res = replace_punctuation(res)
    res = conv.do(res)
    return res


def distribute_phone(n_phone, n_word):
    phones_per_word = [0] * n_word
    for task in range(n_phone):
        min_tasks = min(phones_per_word)
        min_index = phones_per_word.index(min_tasks)
        phones_per_word[min_index] += 1
    return phones_per_word


def g2p(norm_text):

    tokenized = tokenizer.tokenize(norm_text)
    phs = []
    ph_groups = []
    for t in tokenized:
        if not t.startswith("#"):
            ph_groups.append([t])
        else:
            ph_groups[-1].append(t.replace("#", ""))
    word2ph = []
    for group in ph_groups:
        text = ""
        for ch in group:
            text += ch
        if text == "[UNK]":
            phs += ["_"]
            word2ph += [1]
            continue
        elif text in punctuation:
            phs += [text]
            word2ph += [1]
            continue
        # import pdb; pdb.set_trace()
        # phonemes = japanese_text_to_phonemes(text)
        phonemes = kata2phoneme(text)
        # phonemes = [i for i in phonemes if i in symbols]
        for i in phonemes:
            assert i in symbols, (group, norm_text, tokenized, i)
        phone_len = len(phonemes)
        word_len = len(group)

        aaa = distribute_phone(phone_len, word_len)
        assert len(aaa) == word_len
        word2ph += aaa

        phs += phonemes
    phones = ["_"] + phs + ["_"]
    tones = [0 for i in phones]
    word2ph = [1] + word2ph + [1]
    assert len(word2ph) == len(tokenized) + 2
    return phones, tones, word2ph


def get_bert_feature(text, word2ph, device):
    return japanese_bert.get_bert_feature(text, word2ph, device=device)
