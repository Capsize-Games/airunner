import pickle
import os
import re

from airunner.vendor.melo.text import symbols
from airunner.vendor.melo.text.english_utils.abbreviations import (
    expand_abbreviations,
)
from airunner.vendor.melo.text.english_utils.time_norm import (
    expand_time_english,
)
from airunner.vendor.melo.text.english_utils.number_norm import (
    normalize_numbers,
)

from airunner.vendor.melo.text.language_base import LanguageBase
from airunner.vendor.melo.text import english_bert


class English(LanguageBase):
    model_path = "google-bert/bert-base-uncased"
    model_path_bert = "google-bert/bert-base-uncased"

    def __init__(self):
        self.current_file_path = os.path.dirname(__file__)
        self.CMU_DICT_PATH = os.path.join(
            self.current_file_path, "cmudict.rep"
        )
        self.CACHE_PATH = os.path.join(
            self.current_file_path, "cmudict_cache.pickle"
        )
        self.eng_dict = self.get_dict()

        self.arpa = {
            "AH0",
            "S",
            "AH1",
            "EY2",
            "AE2",
            "EH0",
            "OW2",
            "UH0",
            "NG",
            "B",
            "G",
            "AY0",
            "M",
            "AA0",
            "F",
            "AO0",
            "ER2",
            "UH1",
            "IY1",
            "AH2",
            "DH",
            "IY0",
            "EY1",
            "IH0",
            "K",
            "N",
            "W",
            "IY2",
            "T",
            "AA1",
            "ER1",
            "EH2",
            "OY0",
            "UH2",
            "UW1",
            "Z",
            "AW2",
            "AW1",
            "V",
            "UW2",
            "AA2",
            "ER",
            "AW0",
            "UW0",
            "R",
            "OW1",
            "EH1",
            "ZH",
            "AE0",
            "IH2",
            "IH",
            "Y",
            "JH",
            "P",
            "AY1",
            "EY0",
            "OY2",
            "TH",
            "HH",
            "D",
            "ER0",
            "CH",
            "AO1",
            "AE1",
            "AO2",
            "OY1",
            "AY2",
            "IH1",
            "OW0",
            "L",
            "SH",
        }
        super().__init__()

    def distribute_phone(self, n_phone, n_word):
        phones_per_word = [0] * n_word
        for task in range(n_phone):
            min_tasks = min(phones_per_word)
            min_index = phones_per_word.index(min_tasks)
            phones_per_word[min_index] += 1
        return phones_per_word

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
            "v": "V",
        }
        if ph in rep_map.keys():
            ph = rep_map[ph]
        if ph in symbols:
            return ph
        if ph not in symbols:
            ph = "UNK"
        return ph

    def read_dict(
        self,
    ):
        g2p_dict = {}
        start_line = 49
        with open(self.CMU_DICT_PATH) as f:
            line = f.readline()
            line_index = 1
            while line:
                if line_index >= start_line:
                    line = line.strip()
                    word_split = line.split("  ")
                    word = word_split[0]

                    syllable_split = word_split[1].split(" - ")
                    g2p_dict[word] = []
                    for syllable in syllable_split:
                        phone_split = syllable.split(" ")
                        g2p_dict[word].append(phone_split)

                line_index = line_index + 1
                line = f.readline()

        return g2p_dict

    def cache_dict(self, g2p_dict, file_path):
        with open(file_path, "wb") as pickle_file:
            pickle.dump(g2p_dict, pickle_file)

    def get_dict(
        self,
    ):
        if os.path.exists(self.CACHE_PATH):
            with open(self.CACHE_PATH, "rb") as pickle_file:
                g2p_dict = pickle.load(pickle_file)
        else:
            g2p_dict = self.read_dict()
            self.cache_dict(g2p_dict, self.CACHE_PATH)

        return g2p_dict

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

    def text_normalize(self, text):
        text = text.lower()
        text = expand_time_english(text)
        text = normalize_numbers(text)
        text = expand_abbreviations(text)
        return text

    def call(self, text, pad_start_end=True, tokenized=None):
        # Base case: if text is a single character or a word with no spaces and not in eng_dict, return as phone
        if isinstance(text, str) and (len(text.strip().split()) == 1):
            w = text.strip()
            if w.upper() in self.eng_dict:
                phns, tns = self.refine_syllables(self.eng_dict[w.upper()])
                phones = [self.post_replace_ph(i) for i in phns]
                tones = tns
                word2ph = [1] * len(phns)
                if pad_start_end:
                    phones = ["_"] + phones + ["_"]
                    tones = [0] + tones + [0]
                    word2ph = [1] + word2ph + [1]
                return phones, tones, word2ph
            # If not in dict, treat as a sequence of characters (phones)
            if len(w) == 1:
                phones = [self.post_replace_ph(w)]
                tones = [0]
                word2ph = [1]
                if pad_start_end:
                    phones = ["_"] + phones + ["_"]
                    tones = [0] + tones + [0]
                    word2ph = [1] + word2ph + [1]
                return phones, tones, word2ph
        if tokenized is None:
            tokenized = self.tokenizer.tokenize(text)
        # import pdb; pdb.set_trace()
        phs = []
        ph_groups = []
        for t in tokenized:
            if not t.startswith("#"):
                ph_groups.append([t])
            else:
                ph_groups[-1].append(t.replace("#", ""))

        phones = []
        tones = []
        word2ph = []
        for group in ph_groups:
            w = "".join(group)
            phone_len = 0
            word_len = len(group)
            if w.upper() in self.eng_dict:
                phns, tns = self.refine_syllables(self.eng_dict[w.upper()])
                phones += phns
                tones += tns
                phone_len += len(phns)
            else:
                phone_list = list(filter(lambda p: p != " ", self.call(w)))
                # Flatten phone_list if it contains lists
                flat_phone_list = []
                for ph in phone_list:
                    if isinstance(ph, list):
                        flat_phone_list.extend(ph)
                    else:
                        flat_phone_list.append(ph)
                for ph in flat_phone_list:
                    if ph in self.arpa:
                        ph, tn = self.refine_ph(ph)
                        phones.append(ph)
                        tones.append(tn)
                    else:
                        phones.append(ph)
                        tones.append(0)
                    phone_len += 1
            aaa = self.distribute_phone(phone_len, word_len)
            word2ph += aaa
        phones = [self.post_replace_ph(i) for i in phones]

        if pad_start_end:
            phones = ["_"] + phones + ["_"]
            tones = [0] + tones + [0]
            word2ph = [1] + word2ph + [1]
        return phones, tones, word2ph

    def get_bert_feature(self, text, word2ph, device=None):
        return english_bert.get_bert_feature(text, word2ph, device=device)
