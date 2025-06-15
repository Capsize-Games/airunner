import pickle
import torch
import os
from g2p_en import G2p

from airunner.components.application.api.api import API

from transformers import AutoTokenizer, AutoModelForMaskedLM


class LanguageBase:
    model_path = ""
    model_path_bert = ""
    current_file_path = os.path.dirname(__file__)
    CMU_DICT_PATH = os.path.join(current_file_path, "cmudict.rep")
    CACHE_PATH = os.path.join(current_file_path, "cmudict_cache.pickle")

    @staticmethod
    def distribute_phone(n_phone, n_word):
        phones_per_word = [0] * n_word
        for task in range(n_phone):
            min_tasks = min(phones_per_word)
            min_index = phones_per_word.index(min_tasks)
            phones_per_word[min_index] += 1
        return phones_per_word

    @staticmethod
    def unicode_normalize(text):
        import unicodedata

        return unicodedata.normalize("NFKC", text)

    def __init__(self):
        self.logger = API().logger
        self._tokenizer = None
        self._bert_model = None
        self._bert_tokenizer = None
        self.eng_dict = self.get_dict()
        self.current_file_path = os.path.dirname(__file__)
        self.cmu_dict_path = os.path.join(
            self.current_file_path, "cmudict.rep"
        )
        self.cache_path = os.path.join(
            self.current_file_path, "cmudict_cache.pickle"
        )

    @property
    def device(self) -> str:
        if torch.backends.mps.is_available():
            return "mps"
        elif torch.cuda.is_available():
            return "cuda"
        else:
            return "cpu"

    @property
    def bert_model_path(self) -> str:
        return API().paths[self.model_path_bert]

    @property
    def bert_model(self):
        if not self._bert_model:
            try:
                self._bert_model = AutoModelForMaskedLM.from_pretrained(
                    self.bert_model_path
                ).to(self.device)
            except OSError as e:
                self.logger.error(
                    f"Error loading model {self.bert_model_path}: {e}"
                )
        return self._bert_model

    @property
    def bert_tokenizer(self):
        if not self._bert_tokenizer:
            self._bert_tokenizer = AutoTokenizer.from_pretrained(
                self.bert_model_path
            )
        return self._bert_tokenizer

    @property
    def call(self):
        if self._g2p is None:
            self._g2p = G2p()
        return self._g2p

    @property
    def model_id(self):
        return API().paths[self.model_path]

    @property
    def tokenizer(self):
        if self._tokenizer is None:
            self._tokenizer = AutoTokenizer.from_pretrained(self.model_id)
        return self._tokenizer

    @tokenizer.setter
    def tokenizer(self, value):
        self._tokenizer = value

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

    def cache_dict(self, g2p_dict, file_path):
        with open(file_path, "wb") as pickle_file:
            pickle.dump(g2p_dict, pickle_file)

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

    def call(self, text, pad_start_end=True, tokenized=None):
        raise NotImplementedError(
            "g2p method must be implemented in the subclass"
        )

    def get_bert_feature(self, text, word2ph):
        with torch.no_grad():
            inputs = self.bert_tokenizer(text, return_tensors="pt")
            for i in inputs:
                inputs[i] = inputs[i].to(self.device)
            res = self.bert_model(**inputs, output_hidden_states=True)
            res = torch.cat(res["hidden_states"][-3:-2], -1)[0].cpu()
        n_tokens = inputs["input_ids"].shape[-1]
        if len(word2ph) < n_tokens:
            word2ph = list(word2ph) + [1] * (n_tokens - len(word2ph))
        elif len(word2ph) > n_tokens:
            word2ph = list(word2ph)[:n_tokens]
        assert inputs["input_ids"].shape[-1] == len(word2ph)
        word2phone = word2ph
        phone_level_feature = []
        for i in range(len(word2phone)):
            repeat_feature = res[i].repeat(word2phone[i], 1)
            phone_level_feature.append(repeat_feature)
        phone_level_feature = torch.cat(phone_level_feature, dim=0)
        return phone_level_feature.T
