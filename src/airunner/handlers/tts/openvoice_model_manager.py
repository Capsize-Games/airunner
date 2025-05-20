from typing import Type, Optional
from abc import ABCMeta
import os
import torch
from airunner.settings import AIRUNNER_BASE_PATH
from airunner.utils.llm.language import detect_language

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
)
from airunner.handlers.tts.tts_model_manager import TTSModelManager
from airunner.handlers.tts.tts_request import TTSRequest
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
        message = tts_request.message
        language = AvailableLanguage(self.language_settings.bot_language)
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

        self.model.tts_to_file(
            message,
            speaker_ids[speaker_id],
            self.src_path,
            speed=self._speed,
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
        self.logger.debug("Initializing OpenVoice")
        self.unload()
        self.change_model_status(ModelType.TTS, ModelStatus.LOADING)
        self._initialize()
        self.model = TTS(language=self.language)
        self.change_model_status(ModelType.TTS, ModelStatus.LOADED)

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
        pass

    def interrupt_process_signal(self):
        """
        Placeholder for interrupting the TTS process.
        """
        pass

    def _initialize(self):
        """
        Initialize OpenVoice-specific settings and resources.
        """
        try:
            os.makedirs(self._output_dir, exist_ok=True)
        except FileExistsError:
            pass

        if self._reference_speaker is None:
            self.logger.error(
                "Reference speaker is None, unable to initialize"
            )
            return

        try:
            self.logger.info(f"Loading {self._reference_speaker}")
            target_dir = os.path.join(AIRUNNER_BASE_PATH, "processed")
            if not os.path.exists(target_dir):
                os.makedirs(target_dir, exist_ok=True)
            # check if audio_path is valid
            if not os.path.isfile(self._reference_speaker):
                raise FileNotFoundError(
                    f"Reference speaker file {self._reference_speaker} does not exist."
                )
            self._target_se, self._audio_name = se_extractor.get_se(
                audio_path=self._reference_speaker,
                vc_model=self.tone_color_converter,
                target_dir=target_dir,
            )
        except Exception as e:
            torch_hub_cache_home = torch.hub.get_dir()
            self.logger.error(
                f"Failed to load from se_extractor {e} - torch_hub_cache_home={torch_hub_cache_home}"
            )
            self.api.tts.disable()

        if self._target_se is None:
            self.logger.error("Target speaker extraction returned None.")
