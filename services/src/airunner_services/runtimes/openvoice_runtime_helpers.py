"""Helpers for warming and precomputing OpenVoice runtime assets."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import librosa
import torch

from airunner_services.runtimes.file_policy import normalize_local_path
from airunner_common.contract_enums import AvailableLanguage
from airunner_common.settings import AIRUNNER_BASE_PATH, AIRUNNER_LOG_LEVEL
from airunner_services.utils.application.get_logger import get_logger
from airunner_services.runtimes.openvoice_exceptions import FileMissing
from airunner_services.runtimes.openvoice_exceptions import OpenVoiceError
from airunner_tts_vendor.melo.api import TTS
from airunner_tts_vendor.openvoice import se_extractor
from airunner_tts_vendor.openvoice.api import (
    OpenVoiceBaseClass,
    ToneColorConverter,
)
from airunner_tts_vendor.openvoice.mel_processing import spectrogram_torch

logger = get_logger("AI Runner", AIRUNNER_LOG_LEVEL)

#: Longest reference-speaker clip decoded in one load. Reference audio
#: is a few seconds by construction; anything longer is rejected
#: instead of being decoded fully into memory.
MAX_REFERENCE_SPEAKER_SECONDS = 60.0

_DEFAULT_REFERENCE_SPEAKER = (
    Path(__file__).resolve().parents[1]
    / "assets"
    / "reference_speakers"
    / "bobross.wav"
)


def _bundled_reference_speaker_path() -> Optional[str]:
    """Return the bundled reference speaker path when available."""
    if not _DEFAULT_REFERENCE_SPEAKER.is_file():
        return None
    return normalize_local_path(
        str(_DEFAULT_REFERENCE_SPEAKER),
        label="Reference speaker path",
    )


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
                audio_src_path,
                sr=hps.data.sampling_rate,
                mono=True,
                duration=MAX_REFERENCE_SPEAKER_SECONDS,
            )
        except (ValueError, RuntimeError, FileNotFoundError) as error:
            self.logger.error("Error: %s", error)
            return None
        except Exception as error:
            self.logger.error("Error: %s", error)
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
        return _bundled_reference_speaker_path()
    value = str(reference_speaker_path).strip()
    if not value or value == "default":
        return _bundled_reference_speaker_path()
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
    """Create one tone-color converter and load its checkpoint.

    Raises:
        OpenVoiceError: When the config or checkpoint file is missing,
            instead of leaking a bare FileNotFoundError.
    """
    config_path = os.path.join(checkpoint_converter_path, "config.json")
    checkpoint_path = os.path.join(checkpoint_converter_path, "checkpoint.pth")
    for required in (config_path, checkpoint_path):
        if not os.path.isfile(required):
            raise OpenVoiceError(
                f"Tone color converter file is missing: {required}"
            )
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
