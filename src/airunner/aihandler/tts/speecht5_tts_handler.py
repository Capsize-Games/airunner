import os
import time
import torch
from transformers import SpeechT5Processor, SpeechT5ForTextToSpeech, SpeechT5HifiGan
from datasets import load_dataset
from airunner.aihandler.tts.tts_handler import TTSHandler
from airunner.enums import SignalCode, LLMChatRole


class SpeechT5TTSHandler(TTSHandler):
    target_model = "t5"
    model_class_ = SpeechT5ForTextToSpeech
    processor_class_ = SpeechT5Processor

    @property
    def processor_path(self):
        return self.settings["tts_settings"]["speecht5"]["processor_path"]

    @property
    def model_path(self):
        return self.settings["tts_settings"]["speecht5"]["model_path"]

    @property
    def vocoder_path(self):
        return self.settings["tts_settings"]["speecht5"]["vocoder_path"]

    @property
    def speaker_embeddings_dataset_path(self):
        return self.settings["tts_settings"]["speecht5"]["embeddings_path"]

    def load_vocoder(self, local_files_only=True):
        self.logger.debug("Loading Vocoder")
        try:
            self.vocoder = SpeechT5HifiGan.from_pretrained(
                self.vocoder_path,
                local_files_only=local_files_only,
                torch_dtype=torch.float16,
                device_map=self.device
            )
        except OSError as _e:
            return self.load_vocoder(local_files_only=False)

    def load_dataset(self, local_files_only=True):
        """
        load xvector containing speaker's voice characteristics from a dataset
        :return:
        """
        os.environ["HF_DATASETS_OFFLINE"] = str(int(local_files_only))

        embeddings_dataset = None
        self.logger.debug("Loading Dataset")
        try:
            embeddings_dataset = load_dataset(
                self.speaker_embeddings_dataset_path,
                split="validation"
            )
        except OSError as e:
            if local_files_only:
                return self.load_dataset(
                    local_files_only=False
                )
            else:
                self.logger.error("Failed to load dataset")
                self.logger.error(e)
        if embeddings_dataset:
            self.speaker_embeddings = torch.tensor(
                embeddings_dataset[7306]["xvector"]
            ).unsqueeze(0)

        if self.use_cuda and self.speaker_embeddings is not None:
            self.speaker_embeddings = self.speaker_embeddings.half().cuda()

    def do_generate(self, message):
        self.logger.debug("Generating TTS with T5")
        text = self.replace_unspeakable_characters(message)
        text = self.replace_numbers_with_words(text)
        text = text.strip()
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
