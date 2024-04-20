import threading
from typing import Any
import torch
import numpy as np
from airunner.aihandler.base_handler import BaseHandler
from airunner.enums import SignalCode, LLMChatRole
from airunner.utils.clear_memory import clear_memory


class STTHandler(BaseHandler):
    """
    Base class for all Speech-to-Text handlers.
    Override this class to implement a new Speech-to-Text handler.
    """
    listening = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.lock = threading.Lock()
        self.model_path = ""
        self.model = None
        self.model = None
        self.processor = None
        self.feature_extractor = None
        self.model = None
        self.is_on_gpu = False

        if self.settings["stt_enabled"]:
            self.start_capture()

        self.register(SignalCode.STT_PROCESS_AUDIO_SIGNAL, self.on_process_audio)
        self.register(SignalCode.PROCESS_SPEECH_SIGNAL, self.process_given_speech)
        self.register(SignalCode.STT_STOP_CAPTURE_SIGNAL, self.stop_capture)
        self.register(SignalCode.STT_START_CAPTURE_SIGNAL, self.start_capture)
        self.model_type = "stt"
        self.fs = 16000

    def start_capture(self, data: dict = None):
        self.listening = True
        self.loaded = self.load()

    def stop_capture(self, data: dict):
        clear_memory()
        self.listening = False

    def load(self):
        self.model = self.load_model()
        self.processor = self.load_processor()
        self.feature_extractor = self.load_feature_extractor()

        if self.model is not None and self.processor is not None and self.feature_extractor is not None:
            return True
        return False

    @property
    def use_cuda(self):
        return torch.cuda.is_available()

    def on_process_audio(self, data: dict):
        with self.lock:
            audio_data = data["message"]
            # Convert the byte string to a float32 array
            inputs = np.frombuffer(audio_data, dtype=np.int16)
            inputs = inputs.astype(np.float32) / 32767.0
            transcription = self.process_inputs(inputs)
            if transcription is not None:
                self.process_human_speech(transcription)

    def process_inputs(
        self,
        inputs: np.ndarray,
        role: LLMChatRole = LLMChatRole.HUMAN,
    ) -> str:
        transcription = "'"
        try:
            inputs = torch.from_numpy(inputs)
            if torch.isnan(inputs).any():
                self.logger.error("NaN values found after converting numpy array to PyTorch tensor.")
                return
        except Exception as e:
            self.logger.error("Failed to convert numpy array to PyTorch tensor.")
            self.logger.error(e)
            return

        try:
            inputs = self.feature_extractor(inputs, sampling_rate=self.fs, return_tensors="pt")
            if torch.isnan(inputs.input_features).any():
                self.logger.error("NaN values found after feature extraction.")
                return
        except Exception as e:
            self.logger.error("Failed to extract features from inputs.")
            self.logger.error(e)
            return

        try:
            if self.use_cuda:
                inputs["input_features"] = inputs["input_features"].to(torch.bfloat16)
                if torch.isnan(inputs.input_features).any():
                    self.logger.error("NaN values found after converting inputs to BFloat16.")
                    return
        except Exception as e:
            self.logger.error("Failed to convert inputs to BFloat16.")
            self.logger.error(e)
            return

        try:
            inputs = inputs.to(self.model.device)
            if torch.isnan(inputs.input_features).any():
                self.logger.error("NaN values found after moving inputs to device.")
                return
        except Exception as e:
            self.logger.error("Failed to move inputs to device.")
            self.logger.error(e)
            return

        try:
            transcription = self.run(inputs, role)
            if transcription is None or 'nan' in transcription:
                self.logger.error("NaN values found in the transcription.")
                return
        except Exception as e:
            self.logger.error("Failed to run model.")
            self.logger.error(e)
            return

        return transcription

    def load_model(self):
        pass

    def load_processor(self):
        pass

    def load_feature_extractor(self):
        pass

    def move_to_gpu(self):
        if not self.is_on_gpu:
            self.logger.debug("Moving model to GPU")
            self.model = self.model.to(self.device)
            self.processor = self.processor
            self.feature_extractor = self.feature_extractor
            self.is_on_gpu = True

    def move_inputs_to_device(self, inputs):
        if self.use_cuda:
            self.logger.debug("Moving inputs to CUDA")
            try:
                inputs = {k: v.cuda() for k, v in inputs.items()}
            except AttributeError:
                pass
            inputs = inputs.to(torch.bfloat16)
        return inputs

    def run(
        self,
        inputs,
        role: LLMChatRole = LLMChatRole.HUMAN,
    ) -> Any | None:
        """
        Run the model on the given inputs.
        :param inputs: str - The transcription of the audio data.
        :return:
        """
        # Extract the tensor from the BatchFeature object
        try:
            input_tensor = inputs.input_values
        except AttributeError:
            input_tensor = inputs.input_features

        if torch.isnan(input_tensor).any():
            self.logger.error("Inputs contain NaN values.")

        self.logger.debug("Running model")
        input_features = inputs.input_features

        # Generate ids
        if torch.isnan(input_features).any():
            print("Model output contains NaN values.")
            return None

        try:
            # check model.generation_config.lang_to_id for supported languages
            generated_ids = self.model.generate(
                input_features=input_features,
                # generation_config=None,
                # logits_processor=None,
                # stopping_criteria=None,
                # prefix_allowed_tokens_fn=None,
                # synced_gpus=True,
                # return_timestamps=None,
                # task="transcribe",
                # language="en",
                # is_multilingual=True,
                # prompt_ids=None,
                # prompt_condition_type=None,
                # condition_on_prev_tokens=None,
                temperature=0.8,
                # compression_ratio_threshold=None,
                # logprob_threshold=None,
                # no_speech_threshold=None,
                # num_segment_frames=None,
                # attention_mask=None,
                # time_precision=0.02,
                # return_token_timestamps=None,
                # return_segments=False,
                # return_dict_in_generate=None,
            )
        except Exception as e:
            self.logger.error(e)
            return None

        try:
            if torch.isnan(generated_ids).any():
                self.logger.error("Model output contains NaN values.")
        except Exception as e:
            self.logger.error(e)

        try:
            transcription = self.process_transcription(generated_ids)
        except Exception as e:
            self.logger.error(e)
            return None

        if len(transcription) == 0 or len(transcription.split(" ")) == 1:
            return None

        # Emit the transcription so that other handlers can use it
        self.emit_signal(SignalCode.AUDIO_PROCESSOR_RESPONSE_SIGNAL, {
            "transcription": transcription,
            "role": role
        })

        return transcription

    def process_transcription(self, generated_ids):
        # Decode the generated ids
        transcription = self.processor.batch_decode(
            generated_ids,
            skip_special_tokens=True
        )[0]

        # Remove leading and trailing whitespace
        transcription = transcription.strip()

        # Remove any extra whitespace
        transcription = " ".join(transcription.split())

        if False:
            transcription = self.encrypt_transcription(transcription)

        return transcription

    def encrypt_transcription(self, transcription):
        return transcription

    def process_human_speech(self, transcription: str = None):
        """
        Process the human speech.
        This method is called when the model has processed the human speech
        and the transcription is ready to be added to the chat history.
        This should only be used for human speech.
        :param transcription:
        :return:
        """
        self.logger.debug("Processing human speech")
        data = {
            "message": transcription,
            "role": LLMChatRole.HUMAN
        }
        self.emit_signal(SignalCode.ADD_CHATBOT_MESSAGE_SIGNAL, data)
        # self.emit_signal(SignalCode.STT_AUDIO_PROCESSED, {
        #     "message": transcription
        # })

    def process_given_speech(
        self,
        data: dict
    ):
        """
        This is currently used to process the speech from the AI in real time
        in order to simulate the AI hearing itself
        so that heard speech can be added to the chat history
        because we do not want to add all generated text to the history, only the text that the user hears.
        :param data:
        :return:
        """
        self.logger.debug("Processing speech")
        transcription = data["message"]

        if transcription is not None:
            data = {
                "message": transcription,
                "role": data["role"]
            }
            self.emit_signal(SignalCode.ADD_CHATBOT_MESSAGE_SIGNAL, data)
        else:
            self.logger.warning("No AI speech detected")
