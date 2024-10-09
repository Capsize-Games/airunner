import os
import re
import time
from queue import Queue

import inflect
import torch
from transformers import AutoTokenizer

from airunner.handlers.tts.tts_handler import TTSHandler
from airunner.enums import SignalCode, LLMChatRole, ModelType, ModelStatus
from airunner.utils.clear_memory import clear_memory


class SpeechT5TTSHandler(TTSHandler):
    target_model = "t5"

    def __init__(self, *args, **kwargs):
        from transformers import SpeechT5Processor, SpeechT5ForTextToSpeech
        self._model_class_ = SpeechT5ForTextToSpeech
        self._processor_class_ = SpeechT5Processor
        self._current_model = None
        self._character_replacement_map = {
            "\n": " ",
            "’": "'",
            "-": " "
        }
        self._single_character_sentence_enders = [".", "?", "!", "…"]
        self._double_character_sentence_enders = [".”", "?”", "!”", "…”", ".'", "?'", "!'", "…'"]
        self._model = None
        self._vocoder = None
        self._processor = None
        self._text_queue = Queue()
        self._input_text = ""
        self._corpus = []
        self._speaker_embeddings = None
        self._dataset = None
        self._sentences = []
        self._do_interrupt = False
        self._cancel_generated_speech = False
        self._paused = False
        super().__init__(*args, **kwargs)

    @property
    def processor_path(self) -> str:
        path:str = self.speech_t5_settings.processor_path
        return os.path.expanduser(
            os.path.join(
                self.path_settings.base_path,
                "text/models",
                "tts",
                path
            )
        )

    @property
    def model_path(self) -> str:
        path:str = self.speech_t5_settings.model_path
        return os.path.expanduser(
            os.path.join(
                self.path_settings.base_path,
                "text/models",
                "tts",
                path
            )
        )

    @property
    def vocoder_path(self) -> str:
        path:str = self.speech_t5_settings.vocoder_path
        return os.path.expanduser(
            os.path.join(
                self.path_settings.base_path,
                "text/models",
                "tts",
                path
            )
        )

    @property
    def speaker_embeddings_path(self):
        return os.path.expanduser(
            os.path.join(
                self.path_settings.base_path,
                "text/models",
                "tts",
                "datasets",
                "w4ffl35",
                "speecht5_speaker_embeddings",
                "speaker_embeddings"
            )
        )

    def generate(self, message):
        if self.model_status is not ModelStatus.LOADED:
            return None

        if self._do_interrupt or self._paused:
            return None
        try:
            return self._do_generate(message)
        except torch.cuda.OutOfMemoryError:
            self.logger.error("Out of memory")
            return None

    def load(self, target_model=None):
        if self.model_status is ModelStatus.LOADING:
            return
        if self.model_status in (
            ModelStatus.LOADED,
            ModelStatus.READY,
            ModelStatus.FAILED
        ):
            self.unload()
        self.change_model_status(ModelType.TTS, ModelStatus.LOADING)
        self.logger.debug(f"Loading text-to-speech")
        self._load_model()
        self._load_vocoder()
        self._load_processor()
        self._load_speaker_embeddings()
        self._load_tokenizer()
        self._load_corpus()
        self._current_model = self._current_model

        if (
            self._model is not None
            and self._vocoder is not None
            and self._processor is not None
            and self._speaker_embeddings is not None
            and self._tokenizer is not None
            and self._corpus is not None
        ):
            self.change_model_status(ModelType.TTS, ModelStatus.LOADED)
        else:
            self.change_model_status(ModelType.TTS, ModelStatus.FAILED)

    def unload(self):
        if self.model_status is ModelStatus.LOADING:
            return
        self.change_model_status(ModelType.TTS, ModelStatus.LOADING)
        self.logger.debug("Unloading")
        self._unload_model()
        self._unload_processor()
        self._unload_vocoder()
        self._unload_speaker_embeddings()
        self._unload_tokenizer()
        self.change_model_status(ModelType.TTS, ModelStatus.UNLOADED)

    def _load_model(self):
        model_class_ = self._model_class_
        if model_class_ is None:
            return
        self.logger.debug(f"Loading model {self.model_path}")
        try:
            self._model = model_class_.from_pretrained(
                self.model_path,
                local_files_only=True,
                torch_dtype=self.torch_dtype,
                device_map=self.device
            )
        except EnvironmentError as _e:
            self.logger.error(f"Failed to load model {_e}")

    def _load_tokenizer(self):
        self.logger.debug("Loading tokenizer")

        try:
            self._tokenizer = AutoTokenizer.from_pretrained(
                self.model_path,
                device_map=self.device,
                torch_dtype=self.torch_dtype,
                local_files_only=True,
                trust_remote_code=False
            )
        except Exception as e:
            self.logger.error("Failed to load tokenizer")
            self.logger.error(e)

    def _load_vocoder(self):
        self.logger.debug(f"Loading Vocoder {self.vocoder_path}")
        from transformers import SpeechT5HifiGan
        try:
            self._vocoder = self._vocoder = SpeechT5HifiGan.from_pretrained(
                self.vocoder_path,
                local_files_only=True,
                torch_dtype=self.torch_dtype,
                device_map=self.device
            )
        except Exception as e:
            self.logger.error("Failed to load vocoder")
            self.logger.error(e)

    def _load_processor(self):
        self.logger.debug("Loading Procesor")
        processor_class_ = self._processor_class_
        if processor_class_:
            try:
                processor = processor_class_.from_pretrained(
                    self.processor_path,
                    local_files_only=True,
                    torch_dtype=self.torch_dtype,
                    device_map=self.device
                )
                self._processor = processor
            except Exception as e:
                self.logger.error("Failed to load processor")
                self.logger.error(e)

    def _load_corpus(self):
        if self._input_text:
            self.logger.debug("Loading Corpus")
            corpus = open(self._input_text, "r").read()
            for key, value in self._character_replacement_map.items():
                corpus = corpus.replace(key, value)
            self._corpus = corpus.split(" ")

    def _load_speaker_embeddings(self):
        self.logger.debug("Loading speaker embeddings...")

        try:
            self._speaker_embeddings = torch.load(
                self.speaker_embeddings_path
            )
            if self.use_cuda and self._speaker_embeddings is not None:
                self._speaker_embeddings = self._speaker_embeddings.to(torch.bfloat16).cuda()  # Change to bfloat16

        except Exception as e:
            self.logger.error("Failed to load speaker embeddings")
            self.logger.error(e)

    def _unload_speaker_embeddings(self):
        self._speaker_embeddings = None
        clear_memory(self.memory_settings.default_gpu_tts)

    def _do_generate(self, message):
        self.logger.debug("Generating text-to-speech with T5")
        text = self._replace_unspeakable_characters(message)
        text = self._replace_numbers_with_words(text)
        text = text.strip()

        if text == "":
            return None

        self.logger.debug("Processing inputs...")

        inputs = self._processor(
            text=text,
            return_tensors="pt",
            torch_dtype=torch.float16  # Ensure inputs are in float16
        )
        inputs = self._move_inputs_to_device(inputs)

        self.logger.debug("Generating speech...")
        start = time.time()
        self._speaker_embeddings = self._speaker_embeddings.to(torch.float16).to(self.device)
        self._vocoder = self._vocoder.to(torch.float16).to(self.device)

        try:
            speech = self._model.generate(
                **inputs,
                speaker_embeddings=self._speaker_embeddings,
                vocoder=self._vocoder,
                max_length=100
            )
        except RuntimeError as e:
            self.logger.error("Failed to generate speech")
            self.logger.error(e)
            self._cancel_generated_speech = False
            return None

        if not self._cancel_generated_speech:
            self.logger.debug("Generated speech in " + str(time.time() - start) + " seconds")
            response = speech.cpu().float().numpy()
            self.emit_signal(SignalCode.PROCESS_SPEECH_SIGNAL, {
                "message": text,
                "role": LLMChatRole.ASSISTANT
            })
            return response
        if not self._do_interrupt:
            self.logger.debug("Skipping generated speech: " + text)
            self._cancel_generated_speech = False
        return None

    def _move_inputs_to_device(self, inputs):
        use_cuda = self.tts_settings.use_cuda
        if use_cuda:
            self.logger.debug("Moving inputs to CUDA")
            try:
                for key in ("input_ids", "attention_mask"):
                    inputs[key] = inputs[key].to(self.device)

                if "history_prompt" in inputs:
                    for key in ("semantic_prompt", "coarse_prompt", "fine_prompt"):
                        inputs["history_prompt"][key] = inputs["history_prompt"][key].to(self.device)
            except AttributeError as e:
                self.logger.error("Failed to move inputs to CUDA")
                self.logger.error(e)
        return inputs

    @staticmethod
    def _replace_unspeakable_characters(text):
        # strip things like eplisis, etc
        text = text.replace("...", " ")
        text = text.replace("…", " ")
        text = text.replace("’", "'")
        text = text.replace("“", '"')
        text = text.replace("”", '"')
        text = text.replace("‘", "'")
        text = text.replace("’", "'")
        text = text.replace("–", "-")
        text = text.replace("—", "-")

        # replace windows newlines
        text = text.replace("\r\n", " ")

        # replace newlines
        text = text.replace("\n", " ")

        # replace tabs
        text = text.replace("\t", " ")

        # replace excessive spaces
        text = re.sub(r"\s+", " ", text)
        return text

    @staticmethod
    def _replace_numbers_with_words(text):
        p = inflect.engine()
        words = text.split()
        for i in range(len(words)):
            if re.search(r'\d', words[i]):  # check if the word contains a digit
                parts = words[i].split(':')
                parts_in_words = [p.number_to_words(part) if part.isdigit() else part for part in parts]
                words[i] = ':'.join(parts_in_words)

        return ' '.join(words)

    def _unload_model(self):
        self._model = None
        self._current_model = None
        clear_memory(self.memory_settings.default_gpu_tts)

    def _unload_processor(self):
        self._processor = None
        clear_memory(self.memory_settings.default_gpu_tts)

    def _unload_vocoder(self):
        self._vocoder = None
        clear_memory(self.memory_settings.default_gpu_tts)

    def _unload_tokenizer(self):
        self.tokenizer = None
        clear_memory(self.memory_settings.default_gpu_tts)

    def unblock_tts_generator_signal(self):
        self.logger.debug("Unblocking text-to-speech generation...")
        self._do_interrupt = False
        self._paused = False

    def interrupt_process_signal(self):
        self._do_interrupt = True
        self._cancel_generated_speech = False
        self._paused = True
        self._text_queue = Queue()
