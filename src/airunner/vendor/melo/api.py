import os
import re
import soundfile
import numpy as np
import torch.nn as nn
from tqdm import tqdm
import torch
from typing import Dict
from airunner.utils.memory import clear_memory
from airunner.vendor.melo import utils
from airunner.vendor.melo.models import SynthesizerTrn
from airunner.vendor.melo.split_utils import split_sentence
from airunner.vendor.melo.text.cleaner import Cleaner
from airunner.vendor.melo import commons
from airunner.vendor.melo.text import cleaned_text_to_sequence
from airunner.components.application.api.api import API
from airunner.enums import AvailableLanguage


class TTS(nn.Module):
    def __init__(
        self,
        language: AvailableLanguage = AvailableLanguage.EN,
    ):
        super().__init__()
        self.api = API()
        self._language: AvailableLanguage = language
        self.language = language
        self._device: str = None
        self.cleaner = Cleaner()
        self._hps = None
        self._model = None

    @property
    def voice_model_paths(self) -> Dict:
        return {
            AvailableLanguage.EN: self.api.paths[
                "myshell-ai/MeloTTS-English-v3"
            ],
            AvailableLanguage.FR: self.api.paths["myshell-ai/MeloTTS-French"],
            AvailableLanguage.JP: self.api.paths[
                "myshell-ai/MeloTTS-Japanese"
            ],
            AvailableLanguage.ES: self.api.paths["myshell-ai/MeloTTS-Spanish"],
            AvailableLanguage.ZH: self.api.paths["myshell-ai/MeloTTS-Chinese"],
            AvailableLanguage.ZH_MIX_EN: self.api.paths[
                "myshell-ai/MeloTTS-Chinese"
            ],
            AvailableLanguage.KR: self.api.paths["myshell-ai/MeloTTS-Korean"],
        }

    @property
    def ckpt_path(self) -> str:
        model_path = self.voice_model_paths.get(self.language, None)
        if model_path is None:
            raise ValueError(
                f"No model path found for language: {self.language}. Available: {list(self.voice_model_paths.keys())}"
            )
        return os.path.join(model_path, "checkpoint.pth")

    @property
    def checkpoint_dict(self):
        return torch.load(self.ckpt_path, map_location=self.device)

    @property
    def model(self) -> SynthesizerTrn:
        # Only instantiate if self._model is None
        if self._model is None:
            print(f"Loading model from {self.ckpt_path}")
            self._model = SynthesizerTrn(
                len(self.hps.symbols),
                self.hps.data.filter_length // 2 + 1,
                self.hps.train.segment_size // self.hps.data.hop_length,
                n_speakers=self.hps.data.n_speakers,
                num_tones=self.hps.num_tones,
                num_languages=self.hps.num_languages,
                **self.hps.model,
            ).to(self.device)
            self._model.load_state_dict(
                self.checkpoint_dict["model"], strict=True
            )
            self._model.eval()
        return self._model

    @property
    def hps(self) -> utils.HParams:
        if self._hps is None:
            print(f"Loading model from {self.config_path}")
            self._hps = utils.get_hparams_from_file(self.config_path)
        return self._hps

    @property
    def config_path(self) -> str:
        model_path = self.voice_model_paths.get(self.language, None)
        if model_path is None:
            raise ValueError(
                f"No model path found for language: {self.language}. Available: {list(self.voice_model_paths.keys())}"
            )
        return os.path.join(model_path, "config.json")

    @property
    def language(self) -> AvailableLanguage:
        return self._language

    @language.setter
    def language(self, value: AvailableLanguage):
        if not isinstance(value, AvailableLanguage):
            raise ValueError(
                f"Invalid language type: {type(value)}. Expected AvailableLanguage."
            )
        # Only unload if the language actually changes
        if value is not self._language:
            self.unload()
            self.cleaner.language = value
        self._language = value

    @property
    def device(self) -> str:
        if self._device is None:
            self._device = "cpu"
            if torch.cuda.is_available():
                self._device = "cuda"
            if torch.backends.mps.is_available():
                self._device = "mps"
        return self._device

    @staticmethod
    def audio_numpy_concat(segment_data_list, sr, speed=1.0):
        audio_segments = []
        for segment_data in segment_data_list:
            audio_segments += segment_data.reshape(-1).tolist()
            audio_segments += [0] * int((sr * 0.05) / speed)
        audio_segments = np.array(audio_segments).astype(np.float32)
        return audio_segments

    def unload(self):
        if self._model:
            del self._model
            self._model = None
        if self._hps:
            del self._hps
            self._hps = None
        clear_memory()

    def split_sentences_into_pieces(self, text):
        texts = split_sentence(text, language=self.language)
        return texts

    def tts_to_file(
        self,
        text,
        speaker_id,
        output_path=None,
        sdp_ratio=0.2,
        noise_scale=0.6,
        noise_scale_w=0.8,
        speed=1.0,
        pbar=None,
        format=None,
        position=None,
        quiet=False,
    ):
        language = self.language
        texts = self.split_sentences_into_pieces(text)
        audio_list = []
        if pbar:
            tx = pbar(texts)
        else:
            if position:
                tx = tqdm(texts, position=position)
            elif quiet:
                tx = texts
            else:
                tx = tqdm(texts)
        for t in tx:
            if language in [
                AvailableLanguage.EN,
                AvailableLanguage.ZH_MIX_EN,
            ]:
                t = re.sub(r"([a-z])([A-Z])", r"\1 \2", t)
            try:
                bert, ja_bert, phones, tones, lang_ids = (
                    self.get_text_for_tts_infer(t, self.hps)
                )
            except AssertionError as e:
                print(
                    f"Error in text processing: {e}. Skipping this sentence."
                )
                continue
            except NotImplementedError as e:
                print(f"Skipping sentence due to unsupported language: {e}")
                continue
            with torch.no_grad():
                x_tst = phones.to(self.device).unsqueeze(0)
                tones = tones.to(self.device).unsqueeze(0)
                lang_ids = lang_ids.to(self.device).unsqueeze(0)
                bert = bert.to(self.device).unsqueeze(0)
                ja_bert = ja_bert.to(self.device).unsqueeze(0)
                x_tst_lengths = torch.LongTensor([phones.size(0)]).to(
                    self.device
                )
                del phones
                speakers = torch.LongTensor([speaker_id]).to(self.device)

                seq_lens = [
                    x_tst.shape[1],
                    tones.shape[1],
                    lang_ids.shape[1],
                    bert.shape[2],
                    ja_bert.shape[2],
                ]
                target_len = max(seq_lens)

                def pad_tensor(t, dim, target_len, value=0):
                    pad_size = target_len - t.shape[dim]
                    if pad_size > 0:
                        pad_shape = list(t.shape)
                        pad_shape[dim] = pad_size
                        pad = t.new_full(pad_shape, value)
                        return torch.cat([t, pad], dim=dim)
                    elif pad_size < 0:
                        idx = [slice(None)] * len(t.shape)
                        idx[dim] = slice(0, target_len)
                        return t[tuple(idx)]
                    else:
                        return t

                x_tst = pad_tensor(x_tst, 1, target_len)
                tones = pad_tensor(tones, 1, target_len)
                lang_ids = pad_tensor(lang_ids, 1, target_len)
                bert = pad_tensor(bert, 2, target_len)
                ja_bert = pad_tensor(ja_bert, 2, target_len)

                audio = (
                    self.model.infer(
                        x_tst,
                        x_tst_lengths,
                        speakers,
                        tones,
                        lang_ids,
                        bert,
                        ja_bert,
                        sdp_ratio=sdp_ratio,
                        noise_scale=noise_scale,
                        noise_scale_w=noise_scale_w,
                        length_scale=1.0 / speed,
                    )[0][0, 0]
                    .data.cpu()
                    .float()
                    .numpy()
                )
                del (
                    x_tst,
                    tones,
                    lang_ids,
                    bert,
                    ja_bert,
                    x_tst_lengths,
                    speakers,
                )
                #
            audio_list.append(audio)
        torch.cuda.empty_cache()
        audio = self.audio_numpy_concat(
            audio_list, sr=self.hps.data.sampling_rate, speed=speed
        )

        if output_path is None:
            return audio
        else:
            if format:
                soundfile.write(
                    output_path,
                    audio,
                    self.hps.data.sampling_rate,
                    format=format,
                )
            else:
                soundfile.write(
                    output_path, audio, self.hps.data.sampling_rate
                )

    def get_text_for_tts_infer(self, text, hps):
        norm_text, phone, tone, word2ph = self.cleaner.clean_text(
            text, self.language
        )
        symbol_to_id = {s: i for i, s in enumerate(self.hps.symbols)}
        phone, tone, language = cleaned_text_to_sequence(
            phone, tone, self.language, symbol_to_id
        )

        if hps.data.add_blank:
            phone = commons.intersperse(phone, 0)
            tone = commons.intersperse(tone, 0)
            language = commons.intersperse(language, 0)
            for i in range(len(word2ph)):
                word2ph[i] = word2ph[i] * 2
            word2ph[0] += 1

        if getattr(hps.data, "disable_bert", False):
            bert = torch.zeros(1024, len(phone))
            ja_bert = torch.zeros(768, len(phone))
        else:
            bert = self.cleaner.language_module.get_bert_feature(
                norm_text, word2ph
            )

            del word2ph

            lang_enum = self.language
            if lang_enum is AvailableLanguage.ZH:
                bert = bert
                ja_bert = torch.zeros(768, len(phone))
            elif lang_enum in [
                AvailableLanguage.JP,
                AvailableLanguage.EN,
                AvailableLanguage.ZH_MIX_EN,
                AvailableLanguage.KR,
                AvailableLanguage.ES,
                AvailableLanguage.FR,
            ]:
                ja_bert = bert
                bert = torch.zeros(1024, len(phone))
            else:
                print(
                    f"[get_text_for_tts_infer] NotImplementedError: Unsupported language: {lang_enum}"
                )
                raise NotImplementedError(f"Unsupported language: {lang_enum}")

        assert bert.shape[-1] == len(
            phone
        ), f"Bert seq len {bert.shape[-1]} != {len(phone)}"

        phone = torch.LongTensor(phone)
        tone = torch.LongTensor(tone)
        language = torch.LongTensor(language)
        return bert, ja_bert, phone, tone, language
