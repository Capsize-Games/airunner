"""Helpers for warming and precomputing OpenVoice runtime assets."""

from __future__ import annotations

import os
from typing import Optional

import librosa
import torch

from airunner_services.contract_enums import AvailableLanguage
from airunner_services.settings import AIRUNNER_BASE_PATH, AIRUNNER_LOG_LEVEL
from airunner_services.utils.application.get_logger import get_logger
from airunner_services.utils.path_policy import normalize_local_path
from airunner_services.runtimes.openvoice_exceptions import FileMissing
from airunner_services.vendor.melo.api import TTS
from airunner_services.vendor.openvoice import se_extractor
from airunner_services.vendor.openvoice.api import (
    OpenVoiceBaseClass,
    ToneColorConverter,
)
from airunner_services.vendor.openvoice.mel_processing import spectrogram_torch

logger = get_logger("AI Runner", AIRUNNER_LOG_LEVEL)


class StreamingToneColorConverter(ToneColorConverter):
    """Streaming implementation of ToneColorConverter."""

    def __init__(self, *args, **kwargs):
        OpenVoiceBaseClass.__init__(self, *args, **kwargs)
        self.version = getattr(self.hps, "_version_", "v1")
        self.logger = get_logger("AI Runner", AIRUNNER_LOG_LEVEL)

    def convert(
        self,
        audio_src_path,
        src_se,
        tgt_se,
        output_path=None,
        tau=0.3,
        message="default",
    ):
        """Convert audio tone color using the specified parameters."""
        hps = self.hps
        try:
            audio, sample_rate = librosa.load(
                audio_src_path, sr=hps.data.sampling_rate
            )
        except ValueError as error:
            print(f"Error: {error}")
            return None

        if audio is None or len(audio) == 0:
            self.logger.error(
                "Loaded audio is empty for path: %s. Skipping conversion.",
                audio_src_path,
            )
            return None

        audio = torch.tensor(audio).float()
        with torch.no_grad():
            y = torch.FloatTensor(audio).to(self.device).unsqueeze(0)
            try:
                spec = spectrogram_torch(
                    y,
                    hps.data.filter_length,
                    hps.data.sampling_rate,
                    hps.data.hop_length,
                    hps.data.win_length,
                    center=False,
                ).to(self.device)
            except RuntimeError as error:
                self.logger.error(
                    "Runtime error during spectrogram computation: %s",
                    error,
                )
                return None
            spec_lengths = torch.LongTensor([spec.size(-1)]).to(self.device)
            audio = (
                self.model.voice_conversion(
                    spec,
                    spec_lengths,
                    sid_src=src_se,
                    sid_tgt=tgt_se,
                    tau=tau,
                )[0][0, 0]
                .data.cpu()
                .float()
                .numpy()
            )
            return audio


def expand_reference_speaker_path(
    reference_speaker_path: Optional[str],
) -> Optional[str]:
    """Return a normalized reference speaker path or None."""
    if reference_speaker_path is None:
        return None
    value = str(reference_speaker_path).strip()
    if not value or value == "default":
        return None
    return normalize_local_path(value, label="Reference speaker path")


def default_openvoice_device() -> str:
    """Return the preferred OpenVoice execution device."""
    if torch.cuda.is_available():
        return "cuda:0"
    return "cpu"


def build_tone_color_converter(
    checkpoint_converter_path: str,
    device: Optional[str] = None,
) -> StreamingToneColorConverter:
    """Create one tone-color converter and load its checkpoint."""
    resolved_device = device or default_openvoice_device()
    converter = StreamingToneColorConverter(
        os.path.join(checkpoint_converter_path, "config.json"),
        device=resolved_device,
    )
    converter.load_ckpt(
        os.path.join(checkpoint_converter_path, "checkpoint.pth")
    )
    return converter


def processed_target_dir() -> str:
    """Return the shared directory used for cached speaker embeddings."""
    return os.path.join(AIRUNNER_BASE_PATH, "processed")


def ensure_reference_speaker_embedding(
    reference_speaker_path: str,
    converter: StreamingToneColorConverter,
    *,
    target_dir: Optional[str] = None,
):
    """Return one cached or newly extracted speaker embedding."""
    if not os.path.isfile(reference_speaker_path):
        raise FileMissing(reference_speaker_path)

    resolved_target_dir = target_dir or processed_target_dir()
    os.makedirs(resolved_target_dir, exist_ok=True)
    return se_extractor.get_se(
        audio_path=reference_speaker_path,
        vc_model=converter,
        target_dir=resolved_target_dir,
    )


def warm_melo_tts(tts_model: TTS, language: AvailableLanguage) -> None:
    """Force-load the lazy Melo and BERT components used on first synth."""
    tts_model.language = language
    _ = tts_model.hps
    _ = tts_model.model

    cleaner = tts_model.cleaner
    cleaner.language = language
    language_module = cleaner.language_module
    _ = language_module.tokenizer
    _ = language_module.bert_tokenizer
    _ = language_module.bert_model
    tts_model.get_text_for_tts_infer("Warm up.", tts_model.hps)


def precompute_reference_speaker(
    reference_speaker_path: str,
    tts_model_path: str,
) -> bool:
    """Best-effort precompute of one reference speaker embedding."""
    speaker_path = expand_reference_speaker_path(reference_speaker_path)
    if speaker_path is None:
        return False

    checkpoint_path = os.path.join(
        tts_model_path,
        "openvoice/checkpoints_v2/converter",
    )
    converter = build_tone_color_converter(checkpoint_path)
    target_se, _audio_name = ensure_reference_speaker_embedding(
        speaker_path,
        converter,
    )
    return target_se is not None