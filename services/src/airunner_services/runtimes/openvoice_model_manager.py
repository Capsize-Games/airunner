from typing import Type, Optional
from abc import ABCMeta
import os
import tempfile
import threading
from pathlib import Path
from time import perf_counter
import torch

from airunner_common.contract_enums import (
    ModelType,
    ModelStatus,
    AvailableLanguage,
    SignalCode,
)
from airunner_common.settings import AIRUNNER_BASE_PATH
from airunner_services.requests.tts_request import TTSRequest
from airunner_services.runtimes.tts_model_manager import TTSModelManager
from airunner_services.utils.text.language_detection import detect_language
from airunner_services.runtimes.openvoice_file_checker import (
    should_trigger_openvoice_download,
)
from airunner_services.runtimes.openvoice_exceptions import (
    FileMissing,
    OpenVoiceError,
)

torch.hub.set_dir(
    os.environ.get("TORCH_HOME", os.path.join(AIRUNNER_BASE_PATH, "torch/hub"))
)

from airunner_services.utils.memory.clear_memory import clear_memory
from airunner_tts_vendor.melo.api import TTS
from airunner_tts_vendor.melo.api import set_memory_cleanup_hook
from airunner_tts_vendor.melo.runtime_support import (
    normalize_tts_model_root,
    resolve_tts_model_root,
    set_cache_base_resolver,
    set_tts_model_base_resolver,
    set_tts_model_root_resolver,
)
from airunner_services.runtimes.openvoice_runtime_helpers import (
    StreamingToneColorConverter,
    build_tone_color_converter,
    default_openvoice_device,
    ensure_reference_speaker_embedding,
    expand_reference_speaker_path,
    processed_target_dir,
    warm_melo_tts,
)
from airunner_tts_vendor.openvoice.api import ToneColorConverter


def _get_path_settings():
    """Return persisted path settings when available."""
    try:
        from airunner_services.database.models.path_settings import (
            PathSettings,
        )

        return PathSettings.objects.first()
    except Exception:
        return None


def _resolve_configured_tts_model_root() -> Optional[str]:
    """Explicit TTS model root override, if the user configured one.

    Registered with the vendored Melo runtime (issue #2190) so that
    fork has no direct database or settings dependency; this
    replicates the lookup it previously did inline.
    """
    path_settings = _get_path_settings()
    tts_model_path = getattr(path_settings, "tts_model_path", None)
    if tts_model_path:
        return normalize_tts_model_root(tts_model_path)
    return None


def _resolve_tts_model_base() -> str:
    """Base directory the default ``text/models/tts`` root nests under."""
    path_settings = _get_path_settings()
    base_path = getattr(path_settings, "base_path", None)
    if base_path:
        return os.path.expanduser(base_path)
    return AIRUNNER_BASE_PATH


def _readable_file(path: str) -> bool:
    """Return True when one file can actually be opened for reading."""
    try:
        with open(path, "rb"):
            return True
    except OSError:
        return False


def _resolve_cache_base() -> str:
    """Base directory Melo's g2p cache nests under.

    The pre-#2190 implementation always used AIRUNNER_BASE_PATH here
    (unlike the TTS model root, it never consulted PathSettings), so
    this intentionally does not check PathSettings.base_path.
    """
    return AIRUNNER_BASE_PATH


set_tts_model_root_resolver(_resolve_configured_tts_model_root)
set_tts_model_base_resolver(_resolve_tts_model_base)
set_cache_base_resolver(_resolve_cache_base)
# Preserve the previous multi-GPU-aware cleanup exactly (the vendor
# file's own default is a plain gc.collect() + empty_cache()).
set_memory_cleanup_hook(clear_memory)


def _configured_openvoice_root(tts_model_root: str) -> str:
    """Return the OpenVoice asset directory for the active TTS config."""
    configured_path = os.environ.get("AIRUNNER_TTS_MODEL_PATH", "").strip()
    if configured_path:
        candidate = Path(os.path.expanduser(configured_path))
        if candidate.name == "openvoice" or (candidate / "checkpoints_v2").exists():
            return str(candidate)
    return os.path.join(tts_model_root, "openvoice")


class OpenVoiceModelManager(TTSModelManager, metaclass=ABCMeta):
    """
    OpenVoice-based implementation of the TTSModelManager.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._target_se = None
        self._audio_name = None
        self._skip_download_check = False
        self._load_in_progress = False
        self._download_completed = False
        self._generate_lock = threading.Lock()
        self._tts_model_root: str = resolve_tts_model_root()
        self._openvoice_model_root: str = _configured_openvoice_root(
            self._tts_model_root
        )
        self._checkpoint_converter_path: str = os.path.join(
            self._openvoice_model_root,
            "checkpoints_v2/converter",
        )
        self._output_dir: str = os.path.join(
            self._openvoice_model_root,
            "outputs_v2",
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
        if self._should_use_cpu_with_local_llm():
            return "cpu"
        return default_openvoice_device()

    def _should_use_cpu_with_local_llm(self) -> bool:
        """Keep OpenVoice off CUDA while a local LLM is resident."""
        if not torch.cuda.is_available():
            return False
        api = getattr(self, "api", None) or self.refresh_api_reference()
        worker_manager = getattr(api, "_worker_manager", None)
        llm_worker = getattr(worker_manager, "_llm_generate_worker", None)
        if llm_worker is None:
            return False
        status_getter = getattr(llm_worker, "current_model_status", None)
        if callable(status_getter):
            status = status_getter()
            if status in (ModelStatus.LOADED, ModelStatus.READY):
                return True
        model_manager = getattr(llm_worker, "_model_manager", None)
        return getattr(model_manager, "_chat_model", None) is not None

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
                self._openvoice_model_root,
                f"checkpoints_v2/base_speakers/ses/{speaker_key}.pth",
            )
            if not os.path.exists(path):
                path = os.path.join(
                    self._openvoice_model_root,
                    "checkpoints_v2/base_speakers/ses/en-newest.pth",
                )
            if not str(path).endswith(".safetensors"):
                self.logger.warning(
                    "Loading non-safetensors speaker embedding from %s; "
                    "only load embeddings from trusted sources.",
                    path,
                )
            self._source_se = torch.load(
                path,
                map_location=self.device,
                weights_only=True,
            )
        return self._source_se

    def generate(self, tts_request: Type[TTSRequest]):
        """
        Generate speech using OpenVoice and apply tone color conversion.
        """
        if self.model is None:
            raise OpenVoiceError("OpenVoice model is not loaded")
        with self._generate_lock:
            return self._generate_locked(tts_request)

    def _generate_locked(self, tts_request: Type[TTSRequest]):
        """Run one synthesis with per-request temp files.

        The previous implementation shared one fixed ``tmp.wav`` and one
        ``output_v2_<speaker>.wav`` per speaker, so concurrent syntheses
        overwrote each other's audio mid-flight.
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

        os.makedirs(self._output_dir, exist_ok=True)
        src_fd, src_path = tempfile.mkstemp(
            prefix="openvoice-src-", suffix=".wav", dir=self._output_dir
        )
        os.close(src_fd)
        out_fd, output_path = tempfile.mkstemp(
            prefix=f"openvoice-{self.speaker_key}-",
            suffix=".wav",
            dir=self._output_dir,
        )
        os.close(out_fd)
        # Backwards-compatible alias: single-threaded callers that read
        # the last synthesis straight off the manager.
        self.src_path = src_path

        synthesis_start = perf_counter()
        try:
            self.model.tts_to_file(
                message,
                speaker_ids[speaker_id],
                src_path,
                speed=self._speed,
                sdp_ratio=sdp_ratio,
                noise_scale=noise_scale,
                noise_scale_w=noise_scale_w,
            )
        except Exception:
            for stale in (src_path, output_path):
                try:
                    os.unlink(stale)
                except OSError:
                    pass
            raise
        synthesis_elapsed = perf_counter() - synthesis_start

        conversion_start = perf_counter()
        try:
            response = self.tone_color_converter.convert(
                audio_src_path=src_path,
                src_se=self.source_se,
                tgt_se=self._target_se,
                output_path=output_path,
            )
        finally:
            # Both paths are intermediates (convert returns audio, not a
            # path); remove them so per-request temps never accumulate.
            for stale in (src_path, output_path):
                try:
                    os.unlink(stale)
                except OSError:
                    pass
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
        if self._load_in_progress:
            # Re-entrant call from the download-complete callback firing
            # synchronously inside the signal handler below: defer to the
            # outer load instead of recursing the state machine.
            self._skip_download_check = True
            self.logger.debug("OpenVoice load already in progress, deferring")
            return True

        self.logger.debug("Initializing OpenVoice")
        self._load_in_progress = True
        try:
            ready = self._prepare_for_load()
        finally:
            self._load_in_progress = False
        if not ready:
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
            self.model = TTS(
                language=self.language,
                device=self.device,
            )
            self._warm_model_components()
            model_elapsed = perf_counter() - model_start

            self.logger.info(
                "OpenVoice load timings: initialize=%.3fs "
                "tts_init=%.3fs total=%.3fs",
                initialize_elapsed,
                model_elapsed,
                perf_counter() - load_start,
            )
        except Exception:
            self.model = None
            self.change_model_status(ModelType.TTS, ModelStatus.FAILED)
            raise

        self.change_model_status(ModelType.TTS, ModelStatus.LOADED)
        return True

    def _prepare_for_load(self) -> bool:
        """Run the download check, returning True when init may proceed."""
        if self._skip_download_check:
            self._skip_download_check = False
            self.logger.info("Skipping download check after batch download")
            return True
        should_download, _download_info = self._check_and_trigger_download()
        if not should_download:
            return True
        if self._download_completed:
            # The batch download ran synchronously inside the signal
            # handler and the deferred callback already fired: the files
            # are present, so initialize now instead of reporting a
            # pending download.
            self._download_completed = False
            return True
        self.logger.info("OpenVoice model files missing, download triggered")
        return False

    def unload(self):
        """
        Unload the OpenVoice model and release resources.
        """
        self.logger.debug("Unloading OpenVoice")
        self.change_model_status(ModelType.TTS, ModelStatus.LOADING)
        if self.model is not None:
            try:
                self.model.unload()
            except Exception as exc:
                self.logger.warning(
                    "Failed to unload OpenVoice model cleanly: %s",
                    exc,
                )
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
            tts_api = getattr(self.refresh_api_reference(), "tts", None)
            disable = getattr(tts_api, "disable", None)
            if callable(disable):
                disable()
            raise OpenVoiceError(
                f"Failed to load from se_extractor {e} - torch_hub_cache_home={torch_hub_cache_home}"
            )

        if self._target_se is None:
            raise OpenVoiceError("Target speaker extraction returned None.")

    def _warm_model_components(self) -> None:
        """Best-effort warm of the lazy Melo frontend after load."""
        if self.model is None:
            return
        try:
            warm_melo_tts(self.model, self.language)
        except Exception as exc:
            self.logger.debug("OpenVoice warmup skipped: %s", exc)

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
        from airunner_services.database.bootstrap.openvoice_languages import (
            OPENVOICE_CORE_MODELS,
            OPENVOICE_LANGUAGE_MODELS,
        )

        # Check for the converter checkpoint files (from ZIP download).
        # Open each file directly instead of exists()-then-open: the
        # pre-check races a concurrent download or cleanup.
        converter_config = os.path.join(
            self._checkpoint_converter_path, "config.json"
        )
        converter_checkpoint = os.path.join(
            self._checkpoint_converter_path, "checkpoint.pth"
        )
        needs_converter = not _readable_file(
            converter_config
        ) or not _readable_file(converter_checkpoint)

        # Check which core models are missing
        missing_core_models = []
        for model_id in OPENVOICE_CORE_MODELS:
            model_path = os.path.join(
                self._tts_model_root,
                model_id,
            )
            should_download, _ = should_trigger_openvoice_download(
                model_path,
                model_id,
            )
            if should_download:
                missing_core_models.append(model_id)

        # Check which language models are missing
        missing_languages = []
        for lang_key, lang_info in OPENVOICE_LANGUAGE_MODELS.items():
            for model_id in lang_info["models"]:
                model_path = os.path.join(
                    self._tts_model_root,
                    model_id,
                )
                should_download, _ = should_trigger_openvoice_download(
                    model_path,
                    model_id,
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
                """Callback after batch download completes.

                Never calls load() directly: when this fires
                synchronously inside the load() signal handler above,
                that would recurse the load state machine. Instead it
                records completion and reloads only when no load is in
                progress; the in-progress load picks the flags up and
                initializes exactly once.
                """
                self._skip_download_check = True
                self._download_completed = True
                if not self._load_in_progress:
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
