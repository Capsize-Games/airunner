import os
import time
import torch
from transformers import SpeechT5Processor, SpeechT5ForTextToSpeech, SpeechT5HifiGan
from datasets import load_from_disk, load_dataset
from airunner.aihandler.tts.tts_handler import TTSHandler
from airunner.enums import SignalCode, LLMChatRole, ModelType, ModelStatus


class SpeechT5TTSHandler(TTSHandler):
    target_model = "t5"
    model_class_ = SpeechT5ForTextToSpeech
    processor_class_ = SpeechT5Processor

    @property
    def dataset_path(self):
        return os.path.expanduser(
            os.path.join(
                self.settings["path_settings"]["tts_datasets_path"],
                self.settings["tts_settings"]["speecht5"]["datasets_path"]
            )
        )

    @property
    def processor_path(self):
        return os.path.expanduser(
            os.path.join(
                self.settings["path_settings"]["tts_model_path"],
                self.settings["tts_settings"]["speecht5"]["processor_path"]
            )
        )

    @property
    def model_path(self):
        return os.path.expanduser(
            os.path.join(
                self.settings["path_settings"]["tts_model_path"],
                self.settings["tts_settings"]["speecht5"]["model_path"]
            )
        )

    @property
    def vocoder_path(self):
        return os.path.expanduser(
            os.path.join(
                self.settings["path_settings"]["tts_model_path"],
                self.settings["tts_settings"]["speecht5"]["vocoder_path"]
            )
        )

    @property
    def speaker_embeddings_path(self):
        return os.path.expanduser(
            os.path.join(
                self.settings["path_settings"]["tts_speaker_embeddings_path"],
                "speaker_embeddings"
            )
        )

    def load_vocoder(self):
        self.logger.debug(f"Loading Vocoder {self.vocoder_path}")
        try:
            self.emit_signal(SignalCode.MODEL_STATUS_CHANGED_SIGNAL, {
                "model": ModelType.TTS_VOCODER,
                "status": ModelStatus.LOADING,
                "path": self.vocoder_path
            })
            vocoder = self.vocoder = SpeechT5HifiGan.from_pretrained(
                self.vocoder_path,
                local_files_only=True,
                torch_dtype=torch.float16,
                device_map=self.device
            )
            self.emit_signal(SignalCode.MODEL_STATUS_CHANGED_SIGNAL, {
                "model": ModelType.TTS_VOCODER,
                "status": ModelStatus.LOADED,
                "path": self.vocoder_path
            })
            return vocoder
        except Exception as e:
            self.emit_signal(SignalCode.MODEL_STATUS_CHANGED_SIGNAL, {
                "model": ModelType.TTS_VOCODER,
                "status": ModelStatus.FAILED,
                "path": self.vocoder_path
            })
            return None

    def load_dataset(self):
        """
        load xvector containing speaker's voice characteristics from a dataset
        :return:
        """
        self.logger.debug("Loading Dataset")

        self.emit_signal(
            SignalCode.MODEL_STATUS_CHANGED_SIGNAL, {
                "model": ModelType.TTS_SPEAKER_EMBEDDINGS,
                "status": ModelStatus.LOADING,
                "path": self.dataset_path
            }
        )
        try:
            self.speaker_embeddings = torch.load(
                self.speaker_embeddings_path
            )
            if self.use_cuda and self.speaker_embeddings is not None:
                self.speaker_embeddings = self.speaker_embeddings.half().cuda()

            self.emit_signal(
                SignalCode.MODEL_STATUS_CHANGED_SIGNAL, {
                    "model": ModelType.TTS_SPEAKER_EMBEDDINGS,
                    "status": ModelStatus.LOADED,
                    "path": self.dataset_path
                }
            )

        except Exception as e:
            self.logger.error("Failed to load speaker embeddings")
            self.logger.error(e)
            self.emit_signal(
                SignalCode.MODEL_STATUS_CHANGED_SIGNAL, {
                    "model": ModelType.TTS_SPEAKER_EMBEDDINGS,
                    "status": ModelStatus.FAILED,
                    "path": self.dataset_path
                }
            )


    def do_generate(self, message):
        self.logger.debug("Generating TTS with T5")
        text = self.replace_unspeakable_characters(message)
        text = self.replace_numbers_with_words(text)
        text = text.strip()

        import soundfile as sf
        inputs = self.processor(text="Hello, sir", return_tensors="pt")
        inputs = self.move_inputs_to_device(inputs)
        speech = self.model.generate_speech(inputs["input_ids"], self.speaker_embeddings, vocoder=self.vocoder)
        speech = speech.cpu().to(torch.float32)
        sf.write("test.wav", speech.numpy(), samplerate=16000)

        if text == "":
            return None

        self.logger.debug("Processing inputs...")

        inputs = self.processor(
            text=text,
            return_tensors="pt"
        )
        inputs = self.move_inputs_to_device(inputs)

        self.logger.debug("Generating speech...")
        start = time.time()
        try:
            speech = self.model.generate(
                **inputs,
                speaker_embeddings=self.speaker_embeddings,
                vocoder=self.vocoder,
                max_length=100
            )
        except RuntimeError as e:
            self.logger.error("Failed to generate speech")
            self.logger.error(e)
            self.cancel_generated_speech = False
            return None
        if not self.cancel_generated_speech:
            self.logger.debug("Generated speech in " + str(time.time() - start) + " seconds")
            response = speech.cpu().float().numpy()
            self.emit_signal(SignalCode.PROCESS_SPEECH_SIGNAL, {
                "message": text,#response,
                "role": LLMChatRole.ASSISTANT
            })
            return response
        if not self.do_interrupt:
            self.logger.debug("Skipping generated speech: " + text)
            self.cancel_generated_speech = False
        return None
