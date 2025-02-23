import os
import re
import time
from queue import Queue
from typing import Optional

import inflect
import torch
from transformers import AutoTokenizer
from datasets import load_dataset

from airunner.handlers.tts.tts_handler import TTSHandler
from airunner.enums import ModelType, ModelStatus, SpeechT5Voices
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
        speakers = {
            SpeechT5Voices.US_MALE.value: "bdl",
            SpeechT5Voices.US_MALE_2.value: "rms",
            SpeechT5Voices.US_FEMALE.value: "slt",
            SpeechT5Voices.US_FEMALE_2.value: "clb",
            SpeechT5Voices.CANADIAN_MALE.value: "jmk",
            SpeechT5Voices.SCOTTISH_MALE.value: "awb",
            SpeechT5Voices.INDIAN_MALE.value: "ksp",
        }
        embeddings_dataset = load_dataset(
            "Matthijs/cmu-arctic-xvectors",
            split="validation"
        )
        speaker_key = speakers[self.speech_t5_settings.voice]
        embeddings = self._load_dataset_by_speaker_key(
            speaker_key,
            embeddings_dataset
        )
        if embeddings is None:
            self.logger.error(
                "Failed to load speaker embeddings. Using fallback"
            )
            embeddings = self._load_dataset_by_speaker_key(
                "slt",
                embeddings_dataset
            )

        self._speaker_embeddings = embeddings
        if self._speaker_embeddings is not None:
            if self.use_cuda:
                self.logger.info("Moving speaker embeddings to CUDA")
                self._speaker_embeddings = self._speaker_embeddings.to(
                    torch.bfloat16
                ).cuda()
        else:
            self.logger.error("Failed to load speaker embeddings")
        
    def _extract_speaker_key(self, filename):
        return filename.split("_")[2]

    def _load_dataset_by_speaker_key(
        self, 
        speaker_key: str,
        embeddings_dataset: Optional[torch.Tensor] = None
    ) -> Optional[torch.Tensor]:
        embeddings = None
        for entry in embeddings_dataset:
            speaker = self._extract_speaker_key(entry["filename"])
            if speaker_key == speaker:
                embeddings = torch.tensor(entry["xvector"]).unsqueeze(0)
                break
        return embeddings

    def reload_speaker_embeddings(self):
        self._unload_speaker_embeddings()
        self._load_speaker_embeddings()

    def _unload_speaker_embeddings(self):
        self._speaker_embeddings = None
        clear_memory(self.memory_settings.default_gpu_tts)

    def _do_generate(self, message):
        self.logger.debug("Generating text-to-speech with T5")
        text = self._prepare_text(message)

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
        except Exception as e:
            self.logger.error("Failed to generate speech")
            self.logger.error(e)
            self._cancel_generated_speech = False
            return None

        if not self._cancel_generated_speech:
            self.logger.debug("Generated speech in " + str(time.time() - start) + " seconds")
            response = speech.cpu().float().numpy()
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

    def _prepare_text(self, text) -> str:
        text = self._replace_unspeakable_characters(text)
        text = self._strip_emoji_characters(text)
        # the following function is currently disabled because we must first find a
        # reliable way to handle the word "I" and distinguish it from the Roman numeral "I"
        # text = self._roman_to_int(text)
        text = self._replace_numbers_with_words(text)
        text = self._replace_misc_with_words(text)
        return text

    def _replace_misc_with_words(self, text) -> str:
        text = text.replace("°F", "degrees Fahrenheit")
        text = text.replace("°C", "degrees Celsius")
        text = text.replace("°", "degrees")
        return text

    @staticmethod
    def _replace_unspeakable_characters(text) -> str:
        # Replace ellipsis and other unspeakable characters
        text = text.replace("...", " ")
        text = text.replace("…", " ")
        text = text.replace("“", "")
        text = text.replace("”", "")
        text = text.replace("–", "")
        text = text.replace("—", "")
        text = text.replace('"', "")
        text = text.replace("-", "")
        text = text.replace("-", "")

        # Replace windows newlines
        text = text.replace("\r\n", " ")

        # Replace newlines
        text = text.replace("\n", " ")

        # Replace tabs
        text = text.replace("\t", " ")

        # Remove single quotes used as quotes but keep apostrophes
        text = re.sub(r"(?<=\W)'|'(?=\W)", "", text)
        text = re.sub(r"‘|’", "", text)

        return text

    @staticmethod
    def _strip_emoji_characters(text) -> str:
        # strip emojis
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F700-\U0001F77F"  # alchemical symbols
            "\U0001F780-\U0001F7FF"  # Geometric Shapes Extended
            "\U0001F800-\U0001F8FF"  # Supplemental Arrows-C
            "\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
            "\U0001FA00-\U0001FA6F"  # Chess Symbols
            "\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
            "\U00002702-\U000027B0"  # Dingbats
            "\U000024C2-\U0001F251"
            "]+", flags=re.UNICODE
        )
        text = emoji_pattern.sub(r'', text)
        return text

    @staticmethod
    def _roman_to_int(text) -> str:
        roman_numerals = {
            'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000
        }

        def convert_roman_to_int(roman):
            total = 0
            prev_value = 0
            for char in reversed(roman):
                value = roman_numerals[char]
                if value < prev_value:
                    total -= value
                else:
                    total += value
                prev_value = value
            return str(total)

        # Replace Roman numerals with their integer values
        result = re.sub(r'\b[IVXLCDM]+\b', lambda match: convert_roman_to_int(match.group(0)), text)
        return result

    @staticmethod
    def _replace_numbers_with_words(text) -> str:
        p = inflect.engine()

        # Handle time formats separately
        text = re.sub(r'(\d+):(\d+)([APap][Mm])', lambda m: f"{p.number_to_words(m.group(1))} {p.number_to_words(m.group(2)).replace('zero', '').replace('-', ' ')} {m.group(3)[0].upper()} {m.group(3)[1].upper()}", text)
        text = re.sub(r'(\d+):(\d+)', lambda m: f"{p.number_to_words(m.group(1))} {p.number_to_words(m.group(2)).replace('-', ' ')}", text)

        # Split text into words and non-word characters
        words = re.findall(r'\d+|\D+', text)

        for i in range(len(words)):
            if words[i].isdigit():  # check if the word is a digit
                words[i] = p.number_to_words(words[i]).replace('-', ' ')

        # Join words with a space to ensure proper spacing
        result = ' '.join(words).replace('  ', ' ')

        # Ensure "PM" and "AM" are correctly spaced
        result = re.sub(r'\b([AP])M\b', r'\1 M', result)

        return result
