import re
import unicodedata

from airunner.vendor.melo.text import symbols
import pdb
from pykakasi import kakasi
from num2words import num2words
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

from airunner.vendor.melo.text.language_base import LanguageBase


class Japanese(LanguageBase):
    model_path = "tohoku-nlp/bert-base-japanese-v3"
    model_path_bert = "tohoku-nlp/bert-base-japanese-v3"

    def __init__(self):
        super().__init__()
        self._RULEMAP1, self._RULEMAP2 = self._makerulemap()
        self.kakasi = kakasi()
        self.kakasi.setMode("J", "K")  # Chinese to Katakana
        self.kakasi.setMode("H", "K")  # Hiragana to Katakana
        self.conv = self.kakasi.getConverter()

    def _makerulemap(self):
        l = [tuple(x.split("/")) for x in _CONVRULES]
        return tuple({k: v for k, v in l if len(k) == i} for i in (1, 2))

    def kata2phoneme(self, text: str) -> str:
        """Convert katakana text to phonemes."""
        text = text.strip()
        res = []
        while text:
            if len(text) >= 2:
                x = self._RULEMAP2.get(text[:2])
                if x is not None:
                    text = text[2:]
                    res += x.split(" ")[1:]
                    continue
            x = self._RULEMAP1.get(text[0])
            if x is not None:
                text = text[1:]
                res += x.split(" ")[1:]
                continue
            res.append(text[0])
            text = text[1:]
        # res = _COLON_RX.sub(":", res)
        return res

    def hira2kata(self, text: str) -> str:
        text = text.translate(_HIRA2KATATRANS)
        return text.replace("う゛", "ヴ")

    def get_tagger(
        self,
    ):
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

    def text2kata(self, text: str) -> str:
        global _TAGGER
        if _TAGGER is None:
            _TAGGER = self.get_tagger()
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
        return self.hira2kata("".join(res))

    def japanese_convert_numbers_to_words(self, text: str) -> str:
        res = _NUMBER_WITH_SEPARATOR_RX.sub(
            lambda m: m[0].replace(",", ""), text
        )
        res = _CURRENCY_RX.sub(
            lambda m: m[2] + _CURRENCY_MAP.get(m[1], m[1]), res
        )
        res = _NUMBER_RX.sub(lambda m: num2words(m[0], lang="ja"), res)
        return res

    def japanese_convert_alpha_symbols_to_words(self, text: str) -> str:
        return "".join([_ALPHASYMBOL_YOMI.get(ch, ch) for ch in text.lower()])

    def japanese_text_to_phonemes(self, text: str) -> str:
        """Convert Japanese text to phonemes."""
        res = unicodedata.normalize("NFKC", text)
        res = self.japanese_convert_numbers_to_words(res)
        res = self.japanese_convert_alpha_symbols_to_words(res)
        res = self.text2kata(res)
        res = self.kata2phoneme(res)
        return res

    def is_japanese_character(self, char):
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

    def replace_punctuation(self, text):
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

    def text_normalize(self, text):
        res = super().unicode_normalize(text)
        res = self.japanese_convert_numbers_to_words(res)
        res = "".join([i for i in res if self.is_japanese_character(i)])
        res = self.replace_punctuation(res)
        res = self.conv.do(res)
        return res

    def call(self, norm_text):
        tokenized = self.tokenizer.tokenize(norm_text)
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
            phonemes = self.kata2phoneme(text)
            for i in phonemes:
                assert i in symbols, (group, norm_text, tokenized, i)
            phone_len = len(phonemes)
            word_len = len(group)
            aaa = self.distribute_phone(phone_len, word_len)
            assert len(aaa) == word_len
            word2ph += aaa
            phs += phonemes
        phones = ["_"] + phs + ["_"]
        tones = [0 for i in phones]
        word2ph = [1] + word2ph + [1]
        assert len(word2ph) == len(tokenized) + 2
        return phones, tones, word2ph
