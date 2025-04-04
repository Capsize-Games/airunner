# Refactored imports for better readability
from typing import Type, Optional
from abc import ABCMeta
import os
import torch
import enum
import librosa

from openvoice.mel_processing import spectrogram_torch
from openvoice import se_extractor
from openvoice.api import OpenVoiceBaseClass, ToneColorConverter
from melo.api import TTS

from airunner.settings import AIRUNNER_TTS_SPEAKER_RECORDING_PATH
from airunner.enums import SignalCode, ModelType, ModelStatus
from airunner.handlers.tts.tts_model_manager import TTSModelManager

class AvailableLanguage(enum.Enum):
    """
    Enum for available languages in OpenVoice.
    """
    EN_NEWEST = "EN_NEWEST"
    EN = "EN"
    ES = "ES"
    FR = "FR"
    ZH = "ZH"
    JP = "JP"
    KR = "KR"

class StreamingToneColorConverter(ToneColorConverter):
    """
    Streaming implementation of ToneColorConverter.
    """
    def __init__(self, *args, **kwargs):
        OpenVoiceBaseClass.__init__(self, *args, **kwargs)
        self.version = getattr(self.hps, '_version_', "v1")

    def convert(
        self, 
        audio_src_path, 
        src_se, 
        tgt_se, 
        output_path=None, 
        tau=0.3, 
        message="default"
    ):
        """
        Convert audio tone color using the specified parameters.
        """
        hps = self.hps
        try:
            audio, sample_rate = librosa.load(
                audio_src_path, 
                sr=hps.data.sampling_rate
            )
        except ValueError as e:
            print(f"Error: {e}")
            return None

        audio = torch.tensor(audio).float()

        with torch.no_grad():
            y = torch.FloatTensor(audio).to(self.device).unsqueeze(0)
            spec = spectrogram_torch(
                y, 
                hps.data.filter_length,
                hps.data.sampling_rate,
                hps.data.hop_length, 
                hps.data.win_length,
                center=False
            ).to(self.device)
            spec_lengths = torch.LongTensor([spec.size(-1)]).to(self.device)
            audio = self.model.voice_conversion(
                spec, 
                spec_lengths, 
                sid_src=src_se, 
                sid_tgt=tgt_se, 
                tau=tau
            )[0][0, 0].data.cpu().float().numpy()
            return audio

class OpenVoiceModelManager(TTSModelManager, metaclass=ABCMeta):
    """
    OpenVoice-based implementation of the TTSModelManager.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        speaker_recording_path = os.path.expanduser(AIRUNNER_TTS_SPEAKER_RECORDING_PATH)
        self._checkpoint_converter_path: str = os.path.join(
            self.path_settings.tts_model_path,
            'openvoice/checkpoints_v2/converter'
        )
        self._output_dir: str = os.path.join(
            self.path_settings.tts_model_path,
            'openvoice/outputs_v2'
        )
        self._tone_color_converter: Optional[Type[ToneColorConverter]] = None
        self.model: Optional[TTS] = None
        self.src_path: str = f'{self._output_dir}/tmp.wav'
        self._speed: float = 1.0
        self._language: AvailableLanguage = AvailableLanguage.EN_NEWEST
        self._reference_speaker = os.path.expanduser(speaker_recording_path)
        self._target_se, self._audio_name = se_extractor.get_se(
            self._reference_speaker, 
            self.tone_color_converter, 
            vad=True
        )

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
                f'{self._checkpoint_converter_path}/config.json',
                device=self.device
            )
            self._tone_color_converter.load_ckpt(
                f'{self._checkpoint_converter_path}/checkpoint.pth'
            )
        return self._tone_color_converter

    def generate(self, message: str):
        """
        Generate speech using OpenVoice and apply tone color conversion.
        """
        speaker_ids = self.model.hps.data.spk2id
        for speaker_key in speaker_ids.keys():
            speaker_id = speaker_ids[speaker_key]
            speaker_key = speaker_key.lower().replace('_', '-')

            source_se = torch.load(
                os.path.join(
                    self.path_settings.tts_model_path,
                    f'openvoice/checkpoints_v2/base_speakers/ses/{speaker_key}.pth', 
                ),
                map_location=self.device
            )

            self.model.tts_to_file(
                message, 
                speaker_id, 
                self.src_path, 
                speed=self._speed
            )

            output_path = os.path.join(
                self.path_settings.tts_model_path,
                f'openvoice/{self._output_dir}/output_v2_{speaker_key}.wav'
            )

            response = self.tone_color_converter.convert(
                audio_src_path=self.src_path, 
                src_se=source_se, 
                tgt_se=self._target_se, 
                output_path=output_path
            )

            if response is not None:
                self.emit_signal(
                    SignalCode.TTS_GENERATOR_WORKER_ADD_TO_STREAM_SIGNAL, 
                    {"message": response}
                )

    def load(self, _target_model=None):
        """
        Load and initialize the OpenVoice model.
        """
        self.logger.debug("Initializing OpenVoice")
        self.unload()
        self.change_model_status(ModelType.TTS, ModelStatus.LOADING)
        self._initialize()
        self.model = TTS(
            language=self._language.value,
            device=self.device
        )
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
        os.makedirs(self._output_dir, exist_ok=True)