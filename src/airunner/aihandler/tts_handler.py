import os

import inflect
import re
import time

import pyttsx3
import torch
from queue import Queue
from transformers import SpeechT5Processor, SpeechT5ForTextToSpeech, SpeechT5HifiGan, BarkModel, BarkProcessor, \
    BitsAndBytesConfig, GPTQConfig
from datasets import load_dataset
from airunner.aihandler.base_handler import BaseHandler
from airunner.enums import SignalCode
from airunner.utils import clear_memory


class TTSHandler(BaseHandler):
    """
    Generates speech from given text. 
    Responsible for managing the model, processor, vocoder, and speaker embeddings.
    Generates using either the SpeechT5 or Bark model.

    Use from a worker to avoid blocking the main thread.
    """

    @property
    def cuda_index(self):
        return self.settings["tts_settings"]["cuda_index"]

    @property
    def processor_path(self):
        if self.use_bark:
            return "suno/bark-small"
        elif self.use_speecht5:
            return "microsoft/speecht5_tts"
        elif self.use_spd:
            return "microsoft/spd"
        else:
            raise ValueError("No model selected")
    
    @property
    def model_path(self):
        if self.use_bark:
            return "suno/bark-small"
        elif self.use_speecht5:
            return "microsoft/speecht5_tts"
        elif self.use_spd:
            return "microsoft/spd"
        else:
            raise ValueError("No model selected")
    
    @property
    def vocoder_path(self):
        return "microsoft/speecht5_hifigan"
    
    @property
    def speaker_embeddings_dataset_path(self):
        return "Matthijs/cmu-arctic-xvectors"

    @property
    def word_chunks(self):
        return self.settings["tts_settings"]["word_chunks"]

    @property
    def use_bark(self):
        return self.settings["tts_settings"]["model"] == "Bark"

    @property
    def use_speecht5(self):
        return self.settings["tts_settings"]["model"] == "SpeechT5"

    @property
    def use_spd(self):
        return self.settings["tts_settings"]["model"] == "SPD"

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.character_replacement_map = {
            "\n": " ",
            "’": "'",
            "-": " "
        }
        self.text_queue = Queue()
        # self.single_character_sentence_enders = [".", "?", "!", "...", "…"]
        # self.double_character_sentence_enders = [".”", "?”", "!”", "...”", "…”", ".'", "?'", "!'", "...'", "…'"]
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
        self.local_files_only = True
        self.loaded = False
        self.model = None
        self.vocoder = None
        self.processor = None
        self.corpus = []
        self.speaker_embeddings = None
        self.sentences = []
        self.tts_enabled = self.settings["tts_enabled"]
        self.engine = None

        self.logger.debug("Loading")
        self.register(
            SignalCode.APPLICATION_SETTINGS_CHANGED_SIGNAL,
            self.on_application_settings_changed_signal
        )

    def on_application_settings_changed_signal(self, _ignore):
        tts_enabled = self.settings["tts_enabled"]
        if tts_enabled != self.tts_enabled:
            self.tts_enabled = tts_enabled
            if not self.tts_enabled:
                self.unload()
                self.logger.debug("Text to Speech is disabled")
            else:
                self.initialize()
                self.logger.debug("Text to Speech is enabled")

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
        target_model = "bark" if self.use_bark else "t5"
        if target_model != self.current_model:
            self.unload()
        self.load(target_model)

    def load(self, target_model=None):
        if self.tts_enabled:
            self.logger.debug("Text to Speech is disabled")
            self.logger.debug(f"Loading {target_model}...")
            target_model = target_model or self.current_model
            if self.current_model is None or self.model is None:
                self.load_model()
            if self.vocoder is None:
                self.load_vocoder()
            if self.processor is None:
                self.load_processor()
            if self.speaker_embeddings is None:
                self.load_dataset()
            if self.corpus is None:
                self.load_corpus()
            self.logger.debug("Setting current model to " + target_model)
            self.current_model = target_model
            self.loaded = True
    
    def unload(self):
        if not self.loaded:
            return
        self.logger.debug("Unloading")
        self.loaded = False
        do_clear_memory = False
        try:
            self.model = None
            do_clear_memory = True
        except AttributeError:
            pass
        try:
            self.processor = None
            do_clear_memory = True
        except AttributeError:
            pass
        try:
            self.vocoder = None
            do_clear_memory = True
        except AttributeError:
            pass
        try:
            self.speaker_embeddings = None
            do_clear_memory = True
        except AttributeError:
            pass
        self.current_model = None

        if do_clear_memory:
            clear_memory()

    def run(self):
        self.logger.debug("Running")
        if self.use_spd:
            if self.engine is None:
                self.engine = pyttsx3.init()
        else:
            self.initialize()
            self.process_sentences()

    def quantization_config(self):
        config = None
        if self.llm_dtype == "8bit":
            self.logger.debug("Loading 8bit model")
            config = BitsAndBytesConfig(
                load_in_4bit=False,
                load_in_8bit=True,
                llm_int8_threshold=200.0,
                llm_int8_has_fp16_weight=False,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type='nf4',
            )
        elif self.llm_dtype == "4bit":
            self.logger.debug("Loading 4bit model")
            config = BitsAndBytesConfig(
                load_in_4bit=True,
                load_in_8bit=False,
                llm_int8_threshold=200.0,
                llm_int8_has_fp16_weight=False,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type='nf4',
            )
        elif self.llm_dtype == "2bit":
            self.logger.debug("Loading 2bit model")
            config = GPTQConfig(
                bits=2,
                dataset="c4",
                tokenizer=self.tokenizer
            )
        return config

    def load_model(self):
        self.logger.debug("Loading Model")
        model_class_ = BarkModel if self.use_bark else SpeechT5ForTextToSpeech
        self.model = model_class_.from_pretrained(
            self.model_path, 
            local_files_only=self.local_files_only,
            torch_dtype=self.torch_dtype,
            device_map=self.device
        )

        if self.use_bark:
            self.model = self.model.to_bettertransformer()
            self.model.enable_cpu_offload()
    
    def load_vocoder(self, local_files_only=True):
        if not self.use_bark:
            self.logger.debug("Loading Vocoder")
            try:
                self.vocoder = SpeechT5HifiGan.from_pretrained(
                    self.vocoder_path,
                    local_files_only=local_files_only,
                    torch_dtype=self.torch_dtype,
                    device_map=self.device
                )
            except OSError as _e:
                return self.load_vocoder(local_files_only=False)

    def load_processor(self, local_files_only=True):
        self.logger.debug("Loading Procesor")
        processor_class_ = BarkProcessor if self.use_bark else SpeechT5Processor
        try:
            self.processor = processor_class_.from_pretrained(
                self.processor_path,
                local_files_only=local_files_only
            )
        except OSError as _e:
            return self.load_processor(local_files_only=False)

        if self.use_cuda:
            self.processor = self.processor

    def load_dataset(self, local_files_only=True):
        """
        load xvector containing speaker's voice characteristics from a dataset
        :return:
        """
        os.environ["HF_DATASETS_OFFLINE"] = str(int(local_files_only))

        if not self.use_bark:
            self.logger.debug("Loading Dataset")
            try:
                embeddings_dataset = load_dataset(
                    self.speaker_embeddings_dataset_path,
                    split="validation"
                )
            except OSError as _e:
                return self.load_dataset(
                    local_files_only=False
                )
            self.speaker_embeddings = torch.tensor(
                embeddings_dataset[7306]["xvector"]
            ).unsqueeze(0)
            
            if self.use_cuda:
                self.speaker_embeddings = self.speaker_embeddings.half().cuda()

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

    def process_sentences(self):
        """
        now we have a list of words, but we want a list of sentences. Sentences should
        be limited to 10 words each, but should end with a period, comma, question mark,
        exclamation point, or ellipsis. We'll use a counter to keep track of how many
        words we've added to the current sentence, and a list to store the sentences.
        If the sentence doesn't end with one of the above, we'll keep adding words until
        we find one that does, so its possible that a sentence could be longer than 10
        words.
        :return:
        """
        self.logger.debug("Processing sentences")
        self.sentences = []
        sentence = ""
        for word in self.corpus:
            if len(word) == 0:
                continue
            sentence += word + " "
            if word[-1] in self.single_character_sentence_enders or (
                len(word) > 1 and word[-2:] in self.double_character_sentence_enders
            ):
                # remove all white space from sentence
                sentence = sentence.strip()
                sentence += "\n"
                self.sentences.append(sentence)
                sentence = ""
        if sentence != "":
            self.sentences.append(sentence)

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

    def generate(self, message):
        response = None
        if self.tts_enabled:
            if self.use_bark:
                response = self.generate_with_bark(message)
            elif self.use_speecht5:
                response = self.generate_with_t5(message)
            elif self.use_spd:
                """
                With SPD we instantly generate the speech and return nothing.
                We must call spd-say with the generated speech in quotes.
                Example:
                ```bash
                spd-say "Hello, I am a computer."
                ```
                """
                message = message.replace('"', "'")
                settings = self.settings["tts_settings"]["spd"]
                rate = settings["rate"]
                pitch = settings["pitch"]
                volume = settings["volume"]
                voice = settings["voice"]
                language = settings["language"]
                gender = settings["gender"]

                self.engine.setProperty('voice', 'english+f1')
                self.engine.say(message)
                self.engine.runAndWait()

                # bash_command = (
                #     f'spd-say -w "{message}" '
                #     f'-r {rate} '
                #     f'-p {pitch} '
                #     f'-i {volume} '
                #     f'-l {language} '
                #     f'-y {voice} '
                #     f'-t {voice} '
                # )
                # print(bash_command)
                # os.system(bash_command)
        return response

    def generate_with_bark(self, text):
        self.logger.debug("Generating TTS with Bark...")
        self.logger.debug("Processing inputs...")
        inputs = self.processor(
            text=text,
            voice_preset=self.settings["tts_settings"]["voice"]
        )
        inputs = self.move_inputs_to_device(inputs)

        self.logger.debug("Generating speech...")
        start = time.time()
        params = {
            **inputs,
            'fine_temperature': self.settings["tts_settings"]["fine_temperature"] / 100.0,
            'coarse_temperature': self.settings["tts_settings"]["coarse_temperature"] / 100.0,
            'semantic_temperature': self.settings["tts_settings"]["semantic_temperature"] / 100.0,
        }
        speech = self.model.generate(**params)
        self.logger.debug("Generated speech in " + str(time.time() - start) + " seconds")

        response = speech[0].cpu().float().numpy()
        return response

    def generate_with_t5(self, text):
        self.logger.debug("Generating TTS")
        text = text.replace("\n", " ").strip()
        text = text.replace("\n", " ").strip()
        text = self.replace_numbers_with_words(text)

        self.logger.debug("Processing inputs...")

        inputs = self.processor(
            text=text,
            return_tensors="pt"
        )
        inputs = self.move_inputs_to_device(inputs)

        self.logger.debug("Generating speech...")
        start = time.time()
        print(inputs)
        speech = self.model.generate(
            **inputs,
            speaker_embeddings=self.speaker_embeddings,
            vocoder=self.vocoder,
            max_length=100
        )
        self.logger.debug("Generated speech in " + str(time.time() - start) + " seconds")
        response = speech.cpu().float().numpy()
        return response

    def move_inputs_to_device(self, inputs):
        use_cuda = self.settings["tts_settings"]["use_cuda"]
        if use_cuda:
            self.logger.debug("Moving inputs to CUDA")
            try:
                inputs["input_ids"] = inputs["input_ids"].to(self.device)
                inputs["attention_mask"] = inputs["attention_mask"].to(self.device)
                if "history_prompt" in inputs:
                    inputs["history_prompt"]["semantic_prompt"] = inputs["history_prompt"]["semantic_prompt"].to(
                        self.device
                    )
                    inputs["history_prompt"]["coarse_prompt"] = inputs["history_prompt"]["coarse_prompt"].to(
                        self.device
                    )
                    inputs["history_prompt"]["fine_prompt"] = inputs["history_prompt"]["fine_prompt"].to(
                        self.device
                    )
            except AttributeError as e:
                self.logger.error("Failed to move inputs to CUDA")
                self.logger.error(e)
        return inputs
