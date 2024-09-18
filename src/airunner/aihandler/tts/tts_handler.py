import inflect
import re
from queue import Queue
import torch.cuda
from transformers import AutoTokenizer
from airunner.aihandler.base_handler import BaseHandler
from airunner.enums import ModelType, ModelStatus
from airunner.utils.clear_memory import clear_memory


class TTSHandler(BaseHandler):
    """
    Generates speech from given text. 
    Responsible for managing the model, processor, vocoder, and speaker embeddings.
    Generates using either the SpeechT5 or Bark model.

    Use from a worker to avoid blocking the main thread.
    """
    target_model = None
    model_class_ = None
    processor_class_ = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.character_replacement_map = {
            "\n": " ",
            "’": "'",
            "-": " "
        }
        self.text_queue = Queue()
        self.single_character_sentence_enders = [".", "?", "!", "…"]
        self.double_character_sentence_enders = [".”", "?”", "!”", "…”", ".'", "?'", "!'", "…'"]
        self.sentence_delay_time = 1500
        self.sentence_sample_rate = 20000
        self.sentence_blocking = True
        self.buffer_length = 10
        self.input_text = ""
        self.buffer = []
        self.current_sentence = ""
        self.new_sentence = ""
        self.tts_sentence = None
        self.thread_started = False
        self.is_playing = False
        self.current_model = None
        self.do_offload_to_cpu = True
        self.message = ""
        self.loaded = False
        self.model = None
        self.tokenizer = None
        self.current_tokenizer = None
        self.vocoder = None
        self.processor = None
        self.corpus = []
        self.speaker_embeddings = None
        self.dataset = None
        self.sentences = []
        self.engine = None
        self.do_interrupt = False
        self.cancel_generated_speech = False
        self.paused = False
        self.model_type = ModelType.TTS
        self.model_class = "tts"

    @property
    def tts_enabled(self):
        return self.settings["tts_enabled"]

    @tts_enabled.setter
    def tts_enabled(self, value):
        settings = self.settings
        settings["tts_enabled"] = value
        self.settings = settings

    @property
    def cuda_index(self):
        return self.settings["tts_settings"]["cuda_index"]

    @property
    def processor_path(self):
        return ""
    
    @property
    def model_path(self):
        return ""
    
    @property
    def vocoder_path(self):
        pass
    
    @property
    def speaker_embeddings_dataset_path(self):
        pass

    @property
    def word_chunks(self):
        return self.settings["tts_settings"]["word_chunks"]

    @property
    def voice_preset(self):
        return self.settings["tts_settings"]["voice"]

    @property
    def fine_temperature(self):
        return self.settings["tts_settings"]["fine_temperature"] / 100
    
    @property
    def coarse_temperature(self):
        return self.settings["tts_settings"]["coarse_temperature"] / 100
    
    @property
    def semantic_temperature(self):
        return self.settings["tts_settings"]["semantic_temperature"] / 100
    
    @property
    def enable_cpu_offload(self):
        return self.settings["tts_settings"]["enable_cpu_offload"]
    
    @property
    def play_queue_buffer_length(self):
        return self.settings["tts_settings"]["play_queue_buffer_length"]
    
    @property
    def use_word_chunks(self):
        return self.settings["tts_settings"]["use_word_chunks"]
    
    @property
    def use_sentence_chunks(self):
        return self.settings["tts_settings"]["use_sentence_chunks"]

    @property
    def sentence_chunks(self):
        return self.settings["tts_settings"]["sentence_chunks"]

    def enable_tts_signal(self):
        self.tts_enabled = True
        self.initialize()

    def disable_tts_signal(self):
        self.tts_enabled = False
        self.unload()

    def tts_load_signal(self):
        self.load_model()

    def tts_unload_signal(self):
        self.unload_model()

    def tts_processor_load_signal(self):
        self.load_processor()

    def tts_processor_unload_signal(self):
        self.unload_processor()

    def tts_vocoder_load_signal(self):
        self.load_vocoder()

    def tts_vocoder_unload_signal(self):
        self.unload_vocoder()

    def tts_speaker_embeddings_load_signal(self):
        self.load_speaker_embeddings()

    def tts_speaker_embeddings_unload_signal(self):
        self.unload_speaker_embeddings()

    def tts_tokenizer_load_signal(self):
        self.load_tokenizer()

    def tts_tokenizer_unload_signal(self):
        self.unload_tokenizer()

    def dataset_tts_load_signal(self):
        self.load_dataset()

    def dataset_tts_unload_signal(self):
        self.unload_dataset()

    def tts_feature_extractor_load_signal(self):
        self.load_feature_extractor()

    def tts_feature_extractor_unload_signal(self):
        self.unload_feature_extractor()

    def interrupt_process_signal(self):
        self.do_interrupt = True
        self.cancel_generated_speech = False
        self.paused = True
        self.text_queue = Queue()
        self.buffer = []
        self.current_sentence = ""
        self.new_sentence = ""
        self.tts_sentence = None
        self.is_playing = False

    def unblock_tts_generator_signal(self):
        self.logger.debug("Unblocking TTS generation...")
        self.do_interrupt = False
        self.paused = False

    #
    # def application_settings_changed_signal(self):
    #     if not self.tts_enabled:
    #         self.unload()
    #         self.logger.debug("Text to Speech is disabled")
    #     else:
    #         self.initialize()
    #         self.logger.debug("Text to Speech is enabled")

    def move_model(self, to_cpu: bool = False):
        if to_cpu and self.do_offload_to_cpu:
            self.offload_to_cpu()
        else:
            self.move_to_device()
    
    def offload_to_cpu(self):
        """
        Move the model, vocoder, processor and speaker_embeddings to the CPU
        """
        self.logger.debug("Moving TTS to CPU")
        if self.model:
            self.model = self.model.cpu()
        if self.vocoder:
            self.vocoder = self.vocoder.cpu()
        if self.speaker_embeddings:
            self.speaker_embeddings = self.speaker_embeddings.cpu()
    
    def move_to_device(self, device=None):
        """
        Move the model, vocoder, processor and speaker_embeddings to the GPU
        """
        self.logger.debug("Moving TTS to device")
        if self.use_cuda:
            if self.model:
                self.model = self.model.to(self.device)
            if self.vocoder:
                self.vocoder = self.vocoder.to(self.device)
            if self.speaker_embeddings:
                self.speaker_embeddings = self.speaker_embeddings.to(self.device)

    def initialize(self):
        target_model = self.target_model
        if target_model != self.current_model and self.current_model != "" and self.current_model is not None:
            self.unload()
        self.load(target_model)

    def load(self, target_model=None):
        if self.tts_enabled and not self.loaded:
            self.logger.debug(f"Loading {target_model}...")
            target_model = target_model or self.current_model
            if self.current_model is None or self.model is None:
                self.load_model()
            if self.vocoder is None:
                self.vocoder = self.load_vocoder()
            if self.processor is None:
                self.processor = self.load_processor()
            if self.speaker_embeddings is None:
                self.load_speaker_embeddings()
            if self.dataset is None:
                self.load_dataset()
            if self.tokenizer is None:
                self.load_tokenizer()
            if self.corpus is None:
                self.corpus = self.load_corpus()
            self.current_model = target_model
            self.loaded = True

    def unload(self):
        if self.loaded:
            self.logger.debug("Unloading")
            self.loaded = False
            self.unload_model()
            self.unload_processor()
            self.unload_vocoder()
            self.unload_speaker_embeddings()
            self.unload_tokenizer()
            self.unload_dataset()

    def run(self):
        self.initialize()

    def load_model(self):
        model_class_ = self.model_class_
        if model_class_ is None:
            return
        self.logger.debug(f"Loading model {self.model_path}")
        try:
            self.change_model_status(ModelType.TTS, ModelStatus.LOADING, self.model_path)
            model = model_class_.from_pretrained(
                self.model_path,
                local_files_only=True,
                torch_dtype=self.torch_dtype,
                device_map=self.device
            )
            self.change_model_status(ModelType.TTS, ModelStatus.LOADED, self.model_path)
            self.model = model
        except EnvironmentError as _e:
            self.logger.error(f"Failed to load model {_e}")
            self.change_model_status(ModelType.TTS, ModelStatus.FAILED, self.model_path)

    def load_tokenizer(self):
        self.logger.debug("Loading tokenizer")

        try:
            tokenizer = AutoTokenizer.from_pretrained(
                self.model_path,
                device_map=self.device,
                torch_dtype=self.torch_dtype,
                local_files_only=True,
                trust_remote_code=False
            )
            self.change_model_status(ModelType.TTS_TOKENIZER, ModelStatus.LOADED, self.model_path)
            return tokenizer
        except Exception as e:
            self.logger.error("Failed to load tokenizer")
            self.logger.error(e)
            self.change_model_status(ModelType.TTS_TOKENIZER, ModelStatus.FAILED, self.model_path)
    
    def load_vocoder(self):
        pass

    def load_processor(self):
        self.logger.debug("Loading Procesor")
        processor_class_ = self.processor_class_
        if processor_class_:
            try:
                self.change_model_status(ModelType.TTS_PROCESSOR, ModelStatus.LOADING, self.processor_path)
                processor = processor_class_.from_pretrained(
                    self.processor_path,
                    local_files_only=True,
                    torch_dtype=self.torch_dtype,
                    device_map=self.device
                )
                self.change_model_status(ModelType.TTS_PROCESSOR, ModelStatus.LOADED, self.processor_path)
                return processor
            except Exception as e:
                self.logger.error("Failed to load processor")
                self.logger.error(e)
                self.change_model_status(ModelType.TTS_PROCESSOR, ModelStatus.FAILED, self.processor_path)

    def load_dataset(self):
        """
        load xvector containing speaker's voice characteristics from a dataset
        :return:
        """
        pass

    def load_corpus(self):
        if self.input_text:
            self.logger.debug("Loading Corpus")
            corpus = open(self.input_text, "r").read()
            for key, value in self.character_replacement_map.items():
                corpus = corpus.replace(key, value)
            self.corpus = corpus.split(" ")

    def replace_numbers_with_words(self, text):
        p = inflect.engine()
        words = text.split()
        for i in range(len(words)):
            if re.search(r'\d', words[i]):  # check if the word contains a digit
                parts = words[i].split(':')
                parts_in_words = [p.number_to_words(part) if part.isdigit() else part for part in parts]
                words[i] = ':'.join(parts_in_words)

        return ' '.join(words)

    def add_text(self, data: dict, is_end_of_message: bool):
        self.initialize()
        self.message += data["message"]
        #if is_end_of_message:
        return self.process_message(is_end_of_message=is_end_of_message)
    
    def process_message(self, is_end_of_message: bool):
        # split text into words
        words = self.message.split()
        # if not is_end_of_message and len(words) < self.word_chunks:
        #     return False
        
        if self.use_word_chunks:
            # combine words into 30 word chunks
            chunks = [' '.join(words[i:i+self.word_chunks]) for i in range(0, len(words), self.word_chunks)]
            if len(chunks) < 30 and not is_end_of_message:
                return False

            self.logger.debug("Adding text to queue...")
        
            for chunk in chunks:
                # add "..." to chunk if it doesn't end with a sentence ender
                # if not any(chunk.endswith(ender) for ender in sentence_enders):
                #     chunk += "..." 

                # add delay to inputs
                chunk = chunk.strip()
                if chunk.startswith("\n") or chunk.startswith(" "):
                    chunk = chunk[1:]
                if chunk.endswith("\n") or chunk.endswith(" "):
                    chunk = chunk[:-1]
                self.text_queue.put({
                    'text': chunk,
                    'is_end_of_message': is_end_of_message
                })
                self.message = ""
        elif self.use_sentence_chunks:
            chunks = []
            sentence_enders = self.single_character_sentence_enders + self.double_character_sentence_enders
            txt = ""
            for index, char in enumerate(self.message):
                txt += char
                if char in sentence_enders:
                    chunks.append(txt)
                    txt = ""
            if txt != "" and is_end_of_message:
                chunks.append(txt)
                                
            if len(chunks) < self.sentence_chunks and not is_end_of_message:
                return False

            for chunk in chunks:
                if chunk.strip() != "":
                    self.text_queue.put({
                        'text': chunk,
                        'is_end_of_message': is_end_of_message
                    })
            self.message = ""
        else:            
            self.text_queue.put({
                'text': self.message,
                'is_end_of_message': is_end_of_message
            })
            self.message = ""

    def do_generate(self, message):
        pass

    def generate(self, message):
        if self.tts_enabled:
            if self.do_interrupt or self.paused:
                return None

            try:
                return self.do_generate(message)
            except torch.cuda.OutOfMemoryError:
                self.logger.error("Out of memory")
                return None

    def replace_unspeakable_characters(self, text):
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

    def move_inputs_to_device(self, inputs):
        use_cuda = self.settings["tts_settings"]["use_cuda"]
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

    def unload_model(self):
        self.model = None
        self.current_model = None
        clear_memory()
        self.change_model_status(ModelType.TTS, ModelStatus.UNLOADED, "")

    def unload_processor(self):
        self.processor = None
        clear_memory()
        self.change_model_status(ModelType.TTS_PROCESSOR, ModelStatus.UNLOADED, "")

    def unload_vocoder(self):
        self.vocoder = None
        clear_memory()
        self.change_model_status(ModelType.TTS_VOCODER, ModelStatus.UNLOADED, "")

    def load_speaker_embeddings(self):
        pass

    def unload_speaker_embeddings(self):
        pass

    def unload_tokenizer(self):
        self.tokenizer = None
        clear_memory()
        self.change_model_status(ModelType.TTS_TOKENIZER, ModelStatus.UNLOADED, "")

    def unload_dataset(self):
        pass

    def load_feature_extractor(self):
        pass

    def unload_feature_extractor(self):
        pass

