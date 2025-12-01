from typing import Type, Optional
from abc import ABCMeta
import os
import torch

from airunner.components.llm.utils.language import detect_language
from airunner.components.tts.managers.exceptions import (
    FileMissing,
    OpenVoiceError,
)
from airunner.components.art.utils.model_file_checker import ModelFileChecker
from airunner.settings import AIRUNNER_BASE_PATH

torch.hub.set_dir(
    os.environ.get("TORCH_HOME", os.path.join(AIRUNNER_BASE_PATH, "torch/hub"))
)
import librosa

from airunner.vendor.openvoice.mel_processing import spectrogram_torch
from airunner.vendor.openvoice import se_extractor
from airunner.vendor.openvoice.api import (
    OpenVoiceBaseClass,
    ToneColorConverter,
)
from airunner.vendor.melo.api import TTS

from airunner.settings import (
    AIRUNNER_BASE_PATH,
    AIRUNNER_LOG_LEVEL,
)
from airunner.enums import (
    ModelType,
    ModelStatus,
    AvailableLanguage,
    SignalCode,
)
from airunner.components.tts.managers.tts_model_manager import TTSModelManager
from airunner.components.tts.managers.tts_request import TTSRequest
from airunner.utils.application.get_logger import get_logger


class StreamingToneColorConverter(ToneColorConverter):
    """
    Streaming implementation of ToneColorConverter.
    """

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
        """
        Convert audio tone color using the specified parameters.
        """
        hps = self.hps
        try:
            audio, sample_rate = librosa.load(
                audio_src_path, sr=hps.data.sampling_rate
            )
        except ValueError as e:
            print(f"Error: {e}")
            return None

        if audio is None or len(audio) == 0:
            self.logger.error(
                f"Loaded audio is empty for path: {audio_src_path}. Skipping conversion."
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
            except RuntimeError as e:
                self.logger.error(
                    f"Runtime error during spectrogram computation: {e}"
                )
                return None
            spec_lengths = torch.LongTensor([spec.size(-1)]).to(self.device)
            audio = (
                self.model.voice_conversion(
                    spec, spec_lengths, sid_src=src_se, sid_tgt=tgt_se, tau=tau
                )[0][0, 0]
                .data.cpu()
                .float()
                .numpy()
            )
            return audio


class OpenVoiceModelManager(TTSModelManager, metaclass=ABCMeta):
    """
    OpenVoice-based implementation of the TTSModelManager.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._target_se = None
        self._audio_name = None
        self._skip_download_check = False  # Flag to skip download check after batch download
        speaker_recording_path = ""
        if self.openvoice_settings.reference_speaker_path is not None:
            speaker_recording_path = os.path.expanduser(
                os.path.join(self.openvoice_settings.reference_speaker_path)
            )
        else:
            self.logger.error(
                "Reference speaker path is None, unable to initialize"
            )
        self._checkpoint_converter_path: str = os.path.join(
            self.path_settings.tts_model_path,
            "openvoice/checkpoints_v2/converter",
        )
        self._output_dir: str = os.path.join(
            self.path_settings.tts_model_path, "openvoice/outputs_v2"
        )
        self._tone_color_converter: Optional[Type[ToneColorConverter]] = None
        self.model: Optional[TTS] = None
        self.src_path: str = f"{self._output_dir}/tmp.wav"
        self._speed: float = 1.0
        self._reference_speaker = speaker_recording_path
        self._language: AvailableLanguage = (
            AvailableLanguage.EN
        )  # Use a private attribute

    @property
    def language(self) -> AvailableLanguage:
        """
        Get the language setting for TTS.
        """
        if hasattr(self, "application_settings") and getattr(
            self.application_settings, "use_detected_language", False
        ):
            language = self.application_settings.detected_language
            lang = AvailableLanguage[language]
        else:
            lang = self._language
        return lang

    @language.setter
    def language(self, value: AvailableLanguage):
        self._language = value

    @property
    def device(self):
        """
        Return the appropriate device based on CUDA availability.
        """
        use_cuda = torch.cuda.is_available()
        card_index = 0
        return f"cuda:{card_index}" if use_cuda else "cpu"

    @property
    def tone_color_converter(self) -> StreamingToneColorConverter:
        """
        Lazy-load the tone color converter.
        """
        if not self._tone_color_converter:
            self._tone_color_converter = StreamingToneColorConverter(
                f"{self._checkpoint_converter_path}/config.json",
                device=self.device,
            )
            self._tone_color_converter.load_ckpt(
                f"{self._checkpoint_converter_path}/checkpoint.pth"
            )
        return self._tone_color_converter

    _source_se: Optional[torch.Tensor] = None

    @property
    def speaker_key(self) -> str:
        """
        Get the speaker key for the TTS model.
        """
        if self.language is AvailableLanguage.EN:
            return "en-newest"
        return self.language.value.lower()

    @property
    def speaker_id(self) -> str:
        # ['EN-US', 'EN-BR', 'EN_INDIA', 'EN-AU', 'EN-Default']
        if self.language is AvailableLanguage.EN:
            return "EN-Default"
        return self.language.value

    @property
    def source_se(self) -> torch.Tensor:
        if self._source_se is None:
            speaker_key = self.speaker_key
            if speaker_key == "en-us":
                speaker_key = "en-newest"
            path = os.path.join(
                self.path_settings.tts_model_path,
                f"openvoice/checkpoints_v2/base_speakers/ses/{speaker_key}.pth",
            )
            if not os.path.exists(path):
                path = os.path.join(
                    self.path_settings.tts_model_path,
                    f"openvoice/checkpoints_v2/base_speakers/ses/en-newest.pth",
                )
            self._source_se = torch.load(
                path,
                map_location=self.device,
            )
        return self._source_se

    def generate(self, tts_request: Type[TTSRequest]):
        """
        Generate speech using OpenVoice and apply tone color conversion.
        """
        message = self._prepare_text(tts_request.message)
        lang = self.language_settings.bot_language
        if lang is None:
            language = AvailableLanguage.EN
        else:
            try:
                language = AvailableLanguage(lang)
            except ValueError:
                language = AvailableLanguage.EN
        if language is AvailableLanguage.AUTO:
            language = detect_language(tts_request.message)
        if self.language != language:
            self._source_se = None
            self.language = language
            self.model.language = self.language
        speaker_ids = self.model.hps.data.spk2id

        speaker_id = self.speaker_id
        if speaker_id not in speaker_ids:
            speaker_id = "EN-Newest"

        # Get expression parameters from settings (stored as 0-100, convert to 0.0-1.0)
        # Higher values = more expressive speech
        settings = self.openvoice_settings
        sdp_ratio = (settings.sdp_ratio if settings.sdp_ratio is not None else 50) / 100.0
        noise_scale = (settings.noise_scale if settings.noise_scale is not None else 80) / 100.0
        noise_scale_w = (settings.noise_scale_w if settings.noise_scale_w is not None else 90) / 100.0

        self.model.tts_to_file(
            message,
            speaker_ids[speaker_id],
            self.src_path,
            speed=self._speed,
            sdp_ratio=sdp_ratio,
            noise_scale=noise_scale,
            noise_scale_w=noise_scale_w,
        )

        output_path = os.path.join(
            self.path_settings.tts_model_path,
            f"openvoice/{self._output_dir}/output_v2_{self.speaker_key}.wav",
        )

        response = self.tone_color_converter.convert(
            audio_src_path=self.src_path,
            src_se=self.source_se,
            tgt_se=self._target_se,
            output_path=output_path,
        )

        if response is not None:
            self.api.tts.add_to_stream(response)

    def load(self, _target_model=None):
        """
        Load and initialize the OpenVoice model.
        """
        # Prevent re-entrancy - if already loading or loaded, skip
        current_status = self._model_status.get(ModelType.TTS, ModelStatus.UNLOADED)
        if current_status in [ModelStatus.LOADING, ModelStatus.LOADED]:
            self.logger.debug(f"OpenVoice already in state {current_status}, skipping load")
            return True
        
        self.logger.debug("Initializing OpenVoice")

        # Skip download check if we just finished a batch download
        if self._skip_download_check:
            self._skip_download_check = False
            self.logger.info("Skipping download check after batch download")
        else:
            # Check for missing files and trigger download if needed
            should_download, download_info = self._check_and_trigger_download()
            if should_download:
                self.logger.info(
                    "OpenVoice model files missing, download triggered"
                )
                return False

        self.change_model_status(ModelType.TTS, ModelStatus.LOADING)
        
        # Only unload if we have a model to unload (not on first load)
        if self.model is not None:
            self.model = None
            
        self._initialize()
        self.model = TTS(language=self.language)
        self.change_model_status(ModelType.TTS, ModelStatus.LOADED)
        return True

    def unload(self):
        """
        Unload the OpenVoice model and release resources.
        """
        self.logger.debug("Unloading OpenVoice")
        self.change_model_status(ModelType.TTS, ModelStatus.LOADING)
        self.model = None
        self.change_model_status(ModelType.TTS, ModelStatus.UNLOADED)

    def unblock_tts_generator_signal(self):
        """
        Placeholder for unblocking TTS generator signal.
        """

    def interrupt_process_signal(self):
        """
        Placeholder for interrupting the TTS process.
        """

    def _initialize(self):
        """
        Initialize OpenVoice-specific settings and resources.
        """
        try:
            os.makedirs(self._output_dir, exist_ok=True)
        except FileExistsError:
            pass

        if self._reference_speaker is None:
            raise OpenVoiceError(
                "Reference speaker is None, unable to initialize"
            )

        try:
            self.logger.info(f"Loading {self._reference_speaker}")
            target_dir = os.path.join(AIRUNNER_BASE_PATH, "processed")
            if not os.path.exists(target_dir):
                os.makedirs(target_dir, exist_ok=True)

            # check if audio_path is valid
            if not os.path.isfile(self._reference_speaker):
                raise FileMissing(self._reference_speaker)

            self._target_se, self._audio_name = se_extractor.get_se(
                audio_path=self._reference_speaker,
                vc_model=self.tone_color_converter,
                target_dir=target_dir,
            )
        except Exception as e:
            torch_hub_cache_home = torch.hub.get_dir()
            self.api.tts.disable()
            raise OpenVoiceError(
                f"Failed to load from se_extractor {e} - torch_hub_cache_home={torch_hub_cache_home}"
            )

        if self._target_se is None:
            raise OpenVoiceError("Target speaker extraction returned None.")

    def _check_and_trigger_download(self):
        """Check for missing OpenVoice model files and trigger download if needed.

        OpenVoice requires multiple components:
        - Converter checkpoints (checkpoints_v2) - from ZIP file
        - Core BERT models (English) - from HuggingFace
        - MeloTTS voice models (per language) - from HuggingFace
        - Language-specific BERT models - from HuggingFace

        Returns:
            Tuple of (should_download, download_info)
        """
        from airunner.components.tts.data.bootstrap.openvoice_bootstrap_data import (
            OPENVOICE_FILES,
        )
        from airunner.components.tts.data.bootstrap.openvoice_languages import (
            OPENVOICE_CORE_MODELS,
            OPENVOICE_LANGUAGE_MODELS,
        )

        # Check for the converter checkpoint files (from ZIP download)
        converter_config = os.path.join(
            self._checkpoint_converter_path, "config.json"
        )
        converter_checkpoint = os.path.join(
            self._checkpoint_converter_path, "checkpoint.pth"
        )
        needs_converter = not os.path.exists(converter_config) or not os.path.exists(converter_checkpoint)

        # Check which core models are missing
        missing_core_models = []
        for model_id in OPENVOICE_CORE_MODELS:
            model_path = os.path.join(
                self.path_settings.base_path,
                "text/models/tts",
                model_id,
            )
            should_download, _ = ModelFileChecker.should_trigger_download(
                model_path=model_path,
                model_type="tts_openvoice",
                model_id=model_id,
            )
            if should_download:
                missing_core_models.append(model_id)

        # Check which language models are missing
        missing_languages = []
        for lang_key, lang_info in OPENVOICE_LANGUAGE_MODELS.items():
            for model_id in lang_info["models"]:
                model_path = os.path.join(
                    self.path_settings.base_path,
                    "text/models/tts",
                    model_id,
                )
                should_download, _ = ModelFileChecker.should_trigger_download(
                    model_path=model_path,
                    model_type="tts_openvoice",
                    model_id=model_id,
                )
                if should_download:
                    if lang_key not in missing_languages:
                        missing_languages.append(lang_key)
                    break  # Found one missing model for this language

        # Determine if this is a first-time setup (core models or converter missing)
        # vs just missing optional language models
        is_first_time_setup = needs_converter or len(missing_core_models) > 0
        
        # Only trigger download for first-time setup (missing core components)
        # Don't show language dialog for optional language models on subsequent loads
        if is_first_time_setup:
            self.logger.info(
                f"OpenVoice first-time setup: converter={needs_converter}, "
                f"{len(missing_core_models)} core models missing"
            )
            
            def on_download_complete():
                """Callback after batch download completes - skip re-checking."""
                self._skip_download_check = True
                self.load()
            
            self.emit_signal(
                SignalCode.START_OPENVOICE_BATCH_DOWNLOAD,
                {
                    "needs_converter": needs_converter,
                    "missing_core_models": missing_core_models,
                    "missing_languages": missing_languages,
                    "callback": on_download_complete,
                },
            )
            return True, {
                "needs_converter": needs_converter,
                "missing_core_models": missing_core_models,
                "missing_languages": missing_languages,
            }

        return False, {}
