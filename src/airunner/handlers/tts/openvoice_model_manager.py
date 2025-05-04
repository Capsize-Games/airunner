from typing import Type, Optional
from abc import ABCMeta
import os
import torch

torch.hub.set_dir(
    os.environ.get(
        "TORCH_HOME", "/home/appuser/.local/share/airunner/torch/hub"
    )
)
import librosa

from openvoice.mel_processing import spectrogram_torch
from openvoice import se_extractor
from openvoice.api import OpenVoiceBaseClass, ToneColorConverter
from melo.api import TTS

from airunner.settings import (
    AIRUNNER_BASE_PATH,
    AIRUNNER_TTS_SPEAKER_RECORDING_PATH,
    AIRUNNER_LOG_LEVEL,
)
from airunner.enums import (
    SignalCode,
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
        speaker_recording_path = os.path.expanduser(
            AIRUNNER_TTS_SPEAKER_RECORDING_PATH
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
        self._language: AvailableLanguage = AvailableLanguage.EN_NEWEST
        self._reference_speaker = os.path.expanduser(speaker_recording_path)

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

    def generate(self, tts_request: Type[TTSRequest]):
        """
        Generate speech using OpenVoice and apply tone color conversion.
        """
        message = tts_request.message
        speaker_ids = self.model.hps.data.spk2id
        for speaker_key in speaker_ids.keys():
            speaker_id = speaker_ids[speaker_key]
            speaker_key = speaker_key.lower().replace("_", "-")

            source_se = torch.load(
                os.path.join(
                    self.path_settings.tts_model_path,
                    f"openvoice/checkpoints_v2/base_speakers/ses/{speaker_key}.pth",
                ),
                map_location=self.device,
            )

            self.model.tts_to_file(
                message, speaker_id, self.src_path, speed=self._speed
            )

            output_path = os.path.join(
                self.path_settings.tts_model_path,
                f"openvoice/{self._output_dir}/output_v2_{speaker_key}.wav",
            )

            response = self.tone_color_converter.convert(
                audio_src_path=self.src_path,
                src_se=source_se,
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
        do_download = False

        import nltk

        nltk.download("averaged_perceptron_tagger_eng")

        # if do_download:
        #     vad, vad_utils = torch.hub.load(
        #         repo_or_dir="snakers4/silero-vad",
        #         model="silero_vad",
        #         force_reload=False,
        #         onnx=False,
        #     )
        self.model = TTS(language=self._language.value, device=self.device)
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
            self._target_se, self._audio_name = se_extractor.get_se(
                audio_path=self._reference_speaker,
                vc_model=self.tone_color_converter,
                vad=True,
                target_dir=os.path.join(AIRUNNER_BASE_PATH, "processed"),
            )
        except AssertionError as e:
            torch_hub_cache_home = torch.hub.get_dir()
            self.logger.error(
                f"Failed to load from se_extractor {e} - torch_hub_cache_home={torch_hub_cache_home}"
            )
            self.api.tts.disable()

        if self._target_se is None:
            self.logger.error("Target speaker extraction returned None.")
