from airunner.vendor.melo.text.chinese import Chinese
from airunner.vendor.melo.text.japanese import Japanese
from airunner.vendor.melo.text.english import English
from airunner.vendor.melo.text.chinese_mix import ChineseMix
from airunner.vendor.melo.text.korean import Korean
from airunner.vendor.melo.text.french import French
from airunner.vendor.melo.text.spanish import Spanish
from airunner.vendor.melo.text import cleaned_text_to_sequence
import copy


class Cleaner:
    def __init__(self):
        self.language_module_map = {
            "ZH": Chinese,
            "JP": Japanese,
            "EN": English,
            "ZH_MIX_EN": ChineseMix,
            "KR": Korean,
            "FR": French,
            "SP": Spanish,
            "ES": Spanish,
        }
        self._language_module = None

    @property
    def language(self):
        return self._language

    @language.setter
    def language(self, value):
        if getattr(self, "_language", None) != value:
            self._language = None
        self._language = value

    @property
    def language_module(self):
        if not self._language_module:
            self._language_module = self.language_module_map[self.language]()
        return self._language_module
    
    @language_module.setter
    def language_module(self, value):
        if getattr(self, "_language_module", None) != value:
            self._language_module = None
        self._language_module = value

    def clean_text(self, text, language):
        self.language = language
        norm_text = self.language_module.text_normalize(text)
        phones, tones, word2ph = self.language_module.call(norm_text)
        return norm_text, phones, tones, word2ph

    def clean_text_bert(self, text, language, device=None):
        self.language = language
        norm_text = self.language_module.text_normalize(text)
        phones, tones, word2ph = self.language_module.call(norm_text)

        word2ph_bak = copy.deepcopy(word2ph)
        for i in range(len(word2ph)):
            word2ph[i] = word2ph[i] * 2
        word2ph[0] += 1
        bert = self.language_module.get_bert_feature(
            norm_text, word2ph, device=device
        )

        return norm_text, phones, tones, word2ph_bak, bert

    def text_to_sequence(self, text, language):
        norm_text, phones, tones, word2ph = self.clean_text(text, language)
        return cleaned_text_to_sequence(phones, tones, language)
