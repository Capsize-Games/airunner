import copy
from importlib import import_module

from airunner_services.vendor.melo.language import Language
from airunner_services.vendor.melo.text import cleaned_text_to_sequence


class Cleaner:
    def __init__(self):
        self.language_module_map = {
            Language.ZH: (
                "airunner_services.vendor.melo.text.chinese",
                "Chinese",
            ),
            Language.JP: (
                "airunner_services.vendor.melo.text.japanese",
                "Japanese",
            ),
            Language.EN: (
                "airunner_services.vendor.melo.text.english",
                "English",
            ),
            Language.ZH_MIX_EN: (
                "airunner_services.vendor.melo.text.chinese_mix",
                "ChineseMix",
            ),
            Language.KR: (
                "airunner_services.vendor.melo.text.korean",
                "Korean",
            ),
            Language.FR: (
                "airunner_services.vendor.melo.text.french",
                "French",
            ),
            Language.SP: (
                "airunner_services.vendor.melo.text.spanish",
                "Spanish",
            ),
            Language.ES: (
                "airunner_services.vendor.melo.text.spanish",
                "Spanish",
            ),
        }
        self._language_module = None
        self._language: Language = Language.EN

    @staticmethod
    def _resolve_language_module(module_path, class_name):
        """Import one language module only when it is first needed."""
        module = import_module(module_path)
        return getattr(module, class_name)

    @property
    def language(self) -> Language:
        return self._language

    @language.setter
    def language(self, value: Language):
        if value is not self._language:
            self.unload()
        self._language = value

    @property
    def language_module(self):
        if not self._language_module:
            lang = self.language
            if lang not in self.language_module_map:
                lang = Language.EN
            module_path, class_name = self.language_module_map[lang]
            language_module = Cleaner._resolve_language_module(
                module_path,
                class_name,
            )
            self._language_module = language_module()
        return self._language_module

    @language_module.setter
    def language_module(self, value):
        if getattr(self, "_language_module", None) != value:
            self._language_module = None
        self._language_module = value

    def clean_text(
        self, text, language: Language = Language.EN
    ):
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
        _norm_text, phones, tones, _word2ph = self.clean_text(text, language)
        return cleaned_text_to_sequence(phones, tones, language)

    def unload(self):
        if self._language_module:
            del self._language_module
            self._language_module = None
