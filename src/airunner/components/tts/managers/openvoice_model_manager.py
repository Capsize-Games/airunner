from typing import Type, Optional
from abc import ABCMeta
import os
from time import perf_counter
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

from airunner.vendor.openvoice.api import ToneColorConverter
from airunner.vendor.melo.api import TTS

from airunner.settings import (
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
from airunner.components.tts.managers.tts_request import OpenVoiceTTSRequest
from airunner.components.tts.managers.openvoice_runtime_helpers import (
    StreamingToneColorConverter,
    build_tone_color_converter,
    default_openvoice_device,
    ensure_reference_speaker_embedding,
    expand_reference_speaker_path,
    precompute_reference_speaker,
    processed_target_dir,
    warm_melo_tts,
)
from airunner.utils.application.get_logger import get_logger


class OpenVoiceModelManager(TTSModelManager, metaclass=ABCMeta):
    """
    OpenVoice-based implementation of the TTSModelManager.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._target_se = None
        self._audio_name = None
        self._skip_download_check = False
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
        self._reference_speaker = expand_reference_speaker_path(
            getattr(self.openvoice_settings, "reference_speaker_path", None)
        )
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
        return default_openvoice_device()

    @property
    def tone_color_converter(self) -> StreamingToneColorConverter:
        """
        Lazy-load the tone color converter.
        """
        if not self._tone_color_converter:
            self._tone_color_converter = build_tone_color_converter(
                self._checkpoint_converter_path,
                device=self.device,
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
        generation_start = perf_counter()
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

        synthesis_start = perf_counter()
        self.model.tts_to_file(
            message,
            speaker_ids[speaker_id],
            self.src_path,
            speed=self._speed,
            sdp_ratio=sdp_ratio,
            noise_scale=noise_scale,
            noise_scale_w=noise_scale_w,
        )
        synthesis_elapsed = perf_counter() - synthesis_start

        output_path = os.path.join(
            self.path_settings.tts_model_path,
            f"openvoice/{self._output_dir}/output_v2_{self.speaker_key}.wav",
        )

        conversion_start = perf_counter()
        response = self.tone_color_converter.convert(
            audio_src_path=self.src_path,
            src_se=self.source_se,
            tgt_se=self._target_se,
            output_path=output_path,
        )
        conversion_elapsed = perf_counter() - conversion_start
        self.logger.info(
            "OpenVoice generate timings: tts_to_file=%.3fs "
            "convert=%.3fs total=%.3fs",
            synthesis_elapsed,
            conversion_elapsed,
            perf_counter() - generation_start,
        )
        return response

    def load(self, _target_model=None):
        """
        Load and initialize the OpenVoice model.
        """
        load_start = perf_counter()
        current_status = self._model_status.get(
            ModelType.TTS,
            ModelStatus.UNLOADED,
        )
        if current_status in [ModelStatus.LOADING, ModelStatus.LOADED]:
            self.logger.debug(
                f"OpenVoice already in state {current_status}, skipping load"
            )
            return True

        self.logger.debug("Initializing OpenVoice")

        if self._skip_download_check:
            self._skip_download_check = False
            self.logger.info("Skipping download check after batch download")
        else:
            should_download, _download_info = self._check_and_trigger_download()
            if should_download:
                self.logger.info(
                    "OpenVoice model files missing, download triggered"
                )
                return False

        self.change_model_status(ModelType.TTS, ModelStatus.LOADING)
        try:
            if self.model is not None:
                self.model.unload()
                self.model = None

            initialize_start = perf_counter()
            self._initialize()
            initialize_elapsed = perf_counter() - initialize_start

            model_start = perf_counter()
            self.model = TTS(language=self.language)
            model_elapsed = perf_counter() - model_start

            warm_start = perf_counter()
            self._warm_model_components()
            warm_elapsed = perf_counter() - warm_start
            self.logger.info(
                "OpenVoice load timings: initialize=%.3fs "
                "tts_init=%.3fs warm=%.3fs total=%.3fs",
                initialize_elapsed,
                model_elapsed,
                warm_elapsed,
                perf_counter() - load_start,
            )
        except Exception:
            self.model = None
            self.change_model_status(ModelType.TTS, ModelStatus.FAILED)
            raise

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

        self._load_target_speaker_embedding()

    @classmethod
    def precompute_reference_speaker(
        cls,
        reference_speaker_path: str,
        tts_model_path: str,
    ) -> bool:
        """Best-effort precompute of one reference speaker embedding."""
        return precompute_reference_speaker(
            reference_speaker_path,
            tts_model_path,
        )

    def reload_speaker_embeddings(
        self,
        reference_speaker_path: Optional[str] = None,
    ) -> None:
        """Reload the target speaker embedding after one path change."""
        self._target_se = None
        self._audio_name = None
        self._load_target_speaker_embedding(reference_speaker_path)

    def _load_target_speaker_embedding(
        self,
        reference_speaker_path: Optional[str] = None,
    ) -> None:
        """Load one cached or newly computed target speaker embedding."""
        embedding_start = perf_counter()
        self._reference_speaker = expand_reference_speaker_path(
            reference_speaker_path
            or getattr(self.openvoice_settings, "reference_speaker_path", None)
        )

        if self._reference_speaker is None:
            raise OpenVoiceError(
                "Reference speaker is None, unable to initialize"
            )

        try:
            self.logger.info(f"Loading {self._reference_speaker}")
            self._target_se, self._audio_name = ensure_reference_speaker_embedding(
                self._reference_speaker,
                self.tone_color_converter,
                target_dir=processed_target_dir(),
            )
            self.logger.info(
                "OpenVoice target speaker embedding ready in %.3fs",
                perf_counter() - embedding_start,
            )
        except Exception as e:
            torch_hub_cache_home = torch.hub.get_dir()
            self.api.tts.disable()
            raise OpenVoiceError(
                f"Failed to load from se_extractor {e} - torch_hub_cache_home={torch_hub_cache_home}"
            )

        if self._target_se is None:
            raise OpenVoiceError("Target speaker extraction returned None.")

    def _warm_model_components(self) -> None:
        """Force-load the lazy frontend and one full synthesis pass."""
        if self.model is None:
            return
        warm_melo_tts(self.model, self.language)
        self._warm_inference_path()

    def _warm_inference_path(self) -> None:
        """Run one tiny synthesis so first user audio is already warm."""
        start = perf_counter()
        self.generate(
            OpenVoiceTTSRequest(
                message="Warm up.",
                gender=getattr(
                    getattr(self, "chatbot", None),
                    "gender",
                    "Male",
                ),
            )
        )
        self.logger.info(
            "OpenVoice full warmup completed in %.3fs",
            perf_counter() - start,
        )

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
