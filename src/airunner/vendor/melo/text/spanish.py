import re

from airunner.vendor.melo.text import symbols
from airunner.vendor.melo.text.es_phonemizer import cleaner as es_cleaner
from airunner.vendor.melo.text.es_phonemizer import es_to_ipa
from airunner.vendor.melo.text.language_base import LanguageBase


class Spanish(LanguageBase):
    model_path = "dccuchile/bert-base-spanish-wwm-uncased"
    model_path_bert = "dccuchile/bert-base-spanish-wwm-uncased"

    def text_normalize(self, text):
        text = es_cleaner.spanish_cleaners(text)
        return text

    def post_replace_ph(self, ph):
        rep_map = {
            "：": ",",
            "；": ",",
            "，": ",",
            "。": ".",
            "！": "!",
            "？": "?",
            "\n": ".",
            "·": ",",
            "、": ",",
            "...": "…",
        }
        if ph in rep_map.keys():
            ph = rep_map[ph]
        if ph in symbols:
            return ph
        if ph not in symbols:
            ph = "UNK"
        return ph

    def refine_ph(self, phn):
        tone = 0
        if re.search(r"\d$", phn):
            tone = int(phn[-1]) + 1
            phn = phn[:-1]
        return phn.lower(), tone

    def refine_syllables(self, syllables):
        tones = []
        phonemes = []
        for phn_list in syllables:
            for i in range(len(phn_list)):
                phn = phn_list[i]
                phn, tone = self.refine_ph(phn)
                phonemes.append(phn)
                tones.append(tone)
        return phonemes, tones

    def call(self, text, pad_start_end=True, tokenized=None):
        if tokenized is None:
            tokenized = self.tokenizer.tokenize(text)
        # import pdb; pdb.set_trace()
        ph_groups = []
        for t in tokenized:
            if not t.startswith("#"):
                ph_groups.append([t])
            else:
                ph_groups[-1].append(t.replace("#", ""))

        phones = []
        tones = []
        word2ph = []
        # print(ph_groups)
        for group in ph_groups:
            w = "".join(group)
            phone_len = 0
            word_len = len(group)
            if w == "[UNK]":
                phone_list = ["UNK"]
            else:
                phone_list = list(
                    filter(lambda p: p != " ", es_to_ipa.es2ipa(w))
                )

            for ph in phone_list:
                phones.append(ph)
                tones.append(0)
                phone_len += 1
            aaa = self.distribute_phone(phone_len, word_len)
            word2ph += aaa
            # print(phone_list, aaa)
            # print('=' * 10)

        if pad_start_end:
            phones = ["_"] + phones + ["_"]
            tones = [0] + tones + [0]
            word2ph = [1] + word2ph + [1]
        return phones, tones, word2ph
