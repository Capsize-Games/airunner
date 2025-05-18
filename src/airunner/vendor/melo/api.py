import os
import re
import torch
import soundfile
import numpy as np
import torch.nn as nn
from tqdm import tqdm
import torch
from airunner.vendor.melo import utils
from airunner.vendor.melo.models import SynthesizerTrn
from airunner.vendor.melo.split_utils import split_sentence
from airunner.vendor.melo.text.cleaner import Cleaner
from airunner.vendor.melo import commons
from airunner.vendor.melo.text import cleaned_text_to_sequence
from airunner.api import API
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
        self.voice_model_paths = {
            AvailableLanguage.EN: self.api.paths["myshell-ai/MeloTTS-English"],
            AvailableLanguage.EN_NEWEST: self.api.paths[
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
        self.cleaner = Cleaner()

        config_path = os.path.join(
            self.voice_model_paths.get(language, None), "config.json"
        )
        hps = utils.get_hparams_from_file(config_path)

        num_languages = hps.num_languages
        num_tones = hps.num_tones
        symbols = hps.symbols

        model = SynthesizerTrn(
            len(symbols),
            hps.data.filter_length // 2 + 1,
            hps.train.segment_size // hps.data.hop_length,
            n_speakers=hps.data.n_speakers,
            num_tones=num_tones,
            num_languages=num_languages,
            **hps.model,
        ).to(self.device)

        model.eval()
        self.model = model
        self.symbol_to_id = {s: i for i, s in enumerate(symbols)}
        self.hps = hps

        # load state_dict
        ckpt_path = os.path.join(
            self.voice_model_paths.get(language, None), "checkpoint.pth"
        )
        checkpoint_dict = torch.load(ckpt_path, map_location=self.device)
        self.model.load_state_dict(checkpoint_dict["model"], strict=True)

    @property
    def language(self) -> AvailableLanguage:
        return self._language

    @language.setter
    def language(self, value: AvailableLanguage):
        if not isinstance(value, AvailableLanguage):
            raise ValueError(
                f"Invalid language type: {type(value)}. Expected AvailableLanguage."
            )
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
                AvailableLanguage.EN_NEWEST,
                AvailableLanguage.ZH_MIX_EN,
            ]:
                t = re.sub(r"([a-z])([A-Z])", r"\1 \2", t)
            try:
                bert, ja_bert, phones, tones, lang_ids = (
                    self.get_text_for_tts_infer(
                        t,
                        self.hps,
                        self.symbol_to_id,
                    )
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

    def get_text_for_tts_infer(self, text, hps, symbol_to_id=None):
        norm_text, phone, tone, word2ph = self.cleaner.clean_text(
            text, self.language
        )
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
                AvailableLanguage.EN_NEWEST,
                AvailableLanguage.ZH_MIX_EN,
                AvailableLanguage.KR,
                AvailableLanguage.ES,
                AvailableLanguage.FR,
                AvailableLanguage.DE,
                AvailableLanguage.RU,
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
