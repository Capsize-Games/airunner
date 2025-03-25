from typing import Type
import os
import torch

import soundfile
import os
import librosa
from openvoice.mel_processing import spectrogram_torch

from openvoice import se_extractor
from openvoice.api import OpenVoiceBaseClass, ToneColorConverter
from melo.api import TTS
import enum

from abc import ABCMeta

import pyttsx3
from airunner.handlers.tts.tts_handler import TTSHandler
from airunner.enums import ModelType, ModelStatus
from airunner.enums import SignalCode


class AvailableLanguage(enum.Enum):
    EN_NEWEST = "EN_NEWEST"
    EN = "EN"
    ES = "ES"
    FR = "FR"
    ZH = "ZH"
    JP = "JP"
    KR = "KR"


class StreamingToneColorConverter(ToneColorConverter):
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
        hps = self.hps
        # load audio
        audio, sample_rate = librosa.load(audio_src_path, sr=hps.data.sampling_rate)
        audio = torch.tensor(audio).float()
        
        with torch.no_grad():
            y = torch.FloatTensor(audio).to(self.device)
            y = y.unsqueeze(0)
            spec = spectrogram_torch(
                y, 
                hps.data.filter_length,
                hps.data.sampling_rate,
                hps.data.hop_length, 
                hps.data.win_length,
                center=False
            ).to(
                self.device
            )
            spec_lengths = torch.LongTensor(
                [spec.size(-1)]
            ).to(
                self.device
            )
            audio = self.model.voice_conversion(
                spec, 
                spec_lengths, 
                sid_src=src_se, 
                sid_tgt=tgt_se, 
                tau=tau
            )[0][0, 0].data.cpu().float().numpy()
            if output_path is None:
                return audio
            else:
                soundfile.write(
                    output_path, 
                    audio, hps.data.sampling_rate
                )


class OpenVoiceHandler(TTSHandler, metaclass=ABCMeta):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        speaker_recording_path = os.path.expanduser('~/Desktop/bob_ross.mp3')
        
        self.ckpt_converter: str = 'checkpoints_v2/converter'
        self.device: str = "cuda:0" if torch.cuda.is_available() else "cpu"
        self.output_dir: str = 'outputs_v2'
        self.tone_color_converter: Type[ToneColorConverter] = StreamingToneColorConverter(
            f'{self.ckpt_converter}/config.json', 
            device=self.device
        )
        self.tone_color_converter.load_ckpt(f'{self.ckpt_converter}/checkpoint.pth')
        self.voice_file_path: str = speaker_recording_path
        self.src_path: str = f'{self.output_dir}/tmp.wav'
        self.speed: float = 1.0
        self.language: AvailableLanguage = AvailableLanguage.EN_NEWEST
        self.reference_speaker = os.path.expanduser(self.voice_file_path)
        self.target_se, self.audio_name = se_extractor.get_se(
            self.reference_speaker, 
            self.tone_color_converter, 
            vad=True
        )

    def generate(self, message: str):
        model = TTS(
            language=self.language.value,
            device=self.device
        )
        speaker_ids = model.hps.data.spk2id

        for speaker_key in speaker_ids.keys():
            speaker_id = speaker_ids[speaker_key]
            speaker_key = speaker_key.lower().replace('_', '-')
            
            source_se = torch.load(
                f'checkpoints_v2/base_speakers/ses/{speaker_key}.pth', 
                map_location=self.device
            )
            
            start_time = message.time()
            model.tts_to_file(message, speaker_id, self.src_path, speed=self.speed)
            tts_time = message.time() - start_time
            print(f"Time spent on tts_to_file for speaker {speaker_key}: {tts_time:.2f} seconds")


            # Run the tone color converter
            save_path = f'{self.output_dir}/output_v2_{speaker_key}.wav'
            encode_message = "@MyShell"
            start_time = message.time()
            response = self.tone_color_converter.convert(
                audio_src_path=self.src_path, 
                src_se=source_se, 
                tgt_se=self.target_se, 
                output_path=save_path,
                message=encode_message
            )
            convert_time = message.time() - start_time
            print(f"Time spent on tone_color_converter.convert for speaker {speaker_key}: {convert_time:.2f} seconds")

            self.emit_signal(SignalCode.TTS_GENERATOR_WORKER_ADD_TO_STREAM_SIGNAL, {
                "message": response
            })


    def load(self, target_model=None):
        self.logger.debug("Initializing OpenVoice")
        self.unload()
        self.change_model_status(ModelType.TTS, ModelStatus.LOADING)
        
        self._initialize()
        self.change_model_status(ModelType.TTS, ModelStatus.LOADED)

    def unload(self):
        self.logger.debug("Unloading OpenVoice")
        self.change_model_status(ModelType.TTS, ModelStatus.LOADING)
        
        self.change_model_status(ModelType.TTS, ModelStatus.UNLOADED)

    def unblock_tts_generator_signal(self):
        pass

    def interrupt_process_signal(self):
        pass

    def _initialize(self):
        vad, vad_utils = torch.hub.load(
            repo_or_dir='snakers4/silero-vad',
            model='silero_vad',
            force_reload=False,
            onnx=False
        )
        os.makedirs(self.output_dir, exist_ok=True)