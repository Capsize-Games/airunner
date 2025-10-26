from airunner.vendor.melo.text.fr_phonemizer import cleaner as fr_cleaner
from airunner.vendor.melo.text.fr_phonemizer import fr_to_ipa

from airunner.vendor.melo.text.language_base import LanguageBase


class French(LanguageBase):
    model_path = "dbmdz/bert-base-french-europeana-cased"
    model_path_bert = "dbmdz/bert-base-french-europeana-cased"

    def text_normalize(self, text):
        text = fr_cleaner.french_cleaners(text)
        return text

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
                    filter(lambda p: p != " ", fr_to_ipa.fr2ipa(w))
                )

            for ph in phone_list:
                phones.append(ph)
                tones.append(0)
                phone_len += 1
            aaa = self.distribute_phone(phone_len, word_len)
            word2ph += aaa

        if pad_start_end:
            phones = ["_"] + phones + ["_"]
            tones = [0] + tones + [0]
            word2ph = [1] + word2ph + [1]
        return phones, tones, word2ph
