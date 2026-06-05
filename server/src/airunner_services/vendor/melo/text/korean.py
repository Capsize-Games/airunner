import re

from airunner_services.vendor.melo.text import punctuation


from airunner_services.vendor.melo.text.ko_dictionary import (
    english_dictionary,
    etc_dictionary,
)
from jamo import hangul_to_jamo

from airunner_services.vendor.melo.text.language_base import LanguageBase


class Korean(LanguageBase):
    model_path = "kykim/bert-kor-base"
    model_path_bert = "kykim/bert-kor-base"

    def __init__(self):
        super().__init__()
        self.g2p_kr = None

    def normalize(self, text):
        text = text.strip()
        # Remove CJK characters that are not pronounceable in Korean TTS.
        # Ranges are kept non-overlapping to avoid CodeQL overlap warnings.
        text = re.sub(
            "["
            "\u2e80-\u2e99"  # CJK Radicals Supplement (⺀-⺙)
            "\u2e9b-\u2ef3"  # CJK Radicals Supplement cont. (⺛-⻳)
            "\u2f00-\u2fd5"  # Kangxi Radicals (⼀-⿕)
            "\u3005"  # 々
            "\u3007"  # 〇
            "\u3021-\u3029"  # Hangzhou numerals (〡-〩)
            "\u3038-\u303b"  # CJK symbols (〸-〻)
            "\u3400-\u4db5"  # CJK Ext A (㐀-䶵)
            "\u4e00-\u9fc3"  # CJK Unified Ideographs (一-鿃)
            "]",
            "",
            text,
        )
        text = self.normalize_with_dictionary(text, etc_dictionary)
        text = self.normalize_english(text)
        text = text.lower()
        return text

    def normalize_with_dictionary(self, text, dic):
        if any(key in text for key in dic.keys()):
            pattern = re.compile(
                "|".join(re.escape(key) for key in dic.keys())
            )
            return pattern.sub(lambda x: dic[x.group()], text)
        return text

    def normalize_english(self, text):
        def fn(m):
            word = m.group()
            if word in english_dictionary:
                return english_dictionary.get(word)
            return word

        text = re.sub("([A-Za-z]+)", fn, text)
        return text

    def korean_text_to_phonemes(self, text, character: str = "hangeul") -> str:
        """

        The input and output values look the same, but they are different in Unicode.

        example :

            input = '하늘' (Unicode : \ud558\ub298), (하 + 늘)
            output = '하늘' (Unicode :\u1112\u1161\u1102\u1173\u11af), (ᄒ + ᅡ + ᄂ + ᅳ + ᆯ)

        """
        if self.g2p_kr is None:
            from g2pkk import G2p

            self.g2p_kr = G2p()

        if character == "english":
            from anyascii import anyascii

            text = self.normalize(text)
            text = self.g2p_kr(text)
            text = anyascii(text)
            return text

        text = self.normalize(text)
        text = self.g2p_kr(text)
        text = list(
            hangul_to_jamo(text)
        )  # '하늘' --> ['ᄒ', 'ᅡ', 'ᄂ', 'ᅳ', 'ᆯ']
        return "".join(text)

    def text_normalize(self, text):
        text = self.normalize(text)
        return text

    def distribute_phone(self, n_phone, n_word):
        phones_per_word = [0] * n_word
        for task in range(n_phone):
            min_tasks = min(phones_per_word)
            min_index = phones_per_word.index(min_tasks)
            phones_per_word[min_index] += 1
        return phones_per_word

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
            phonemes = self.korean_text_to_phonemes(text)
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
