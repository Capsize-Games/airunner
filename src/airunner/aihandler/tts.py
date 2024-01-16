import time
import torch
import sounddevice as sd
import numpy as np

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QThread

from transformers import SpeechT5Processor, SpeechT5ForTextToSpeech, SpeechT5HifiGan, BarkModel, BarkProcessor
from datasets import load_dataset

from airunner.aihandler.logger import Logger


from queue import Queue, Empty
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QThread

class VocalizerWorker(QObject):
    add_to_stream_signal = pyqtSignal(np.ndarray)
    reader_mode_active = False

    def __init__(self, *args, **kwargs):
        super().__init__()
        self.parent = kwargs.get("parent")
        self.queue = Queue()

    def process(self):
        self.stream = sd.OutputStream(samplerate=24000, channels=1)
        self.stream.start()
        data = []
        started = False
        while True:
            try:
                item = self.queue.get(timeout=1)
                if item is None:
                    break
                if started or not self.reader_mode_active:
                    self.stream.write(item)
                else:
                    data.append(item)

                if not started and len(data) >= 6 and self.reader_mode_active:
                    for item in data:
                        self.stream.write(item)
                    started = True
                    data = []
            except Empty:
                continue
        
    def handle_speech(self, generated_speech):
        Logger.info("Adding speech to stream...")
        try:
            self.queue.put(generated_speech)
        except Exception as e:
            print(f"Error while adding speech to stream: {e}")


class GeneratorWorker(QObject):
    add_to_stream_signal = pyqtSignal(np.ndarray)

    def __init__(self, *args, **kwargs):
        super().__init__()
        self.parent = kwargs.get("parent")
    
    @pyqtSlot()
    def process(self):
        # get item from self.parent.text.queue
        play_queue = []
        play_queue_started = False
        while True:
            if not self.parent.text_queue.empty():
                data = self.parent.text_queue.get()
                if not self.parent.engine.app.settings["tts_enabled"]:
                    continue
                play_queue.append(data)
                if data["is_end_of_message"] or len(play_queue) == self.parent.play_queue_buffer_length or play_queue_started:
                    for item in play_queue:
                        self.generate(item["text"])
                    play_queue_started = True
                    play_queue = []
            time.sleep(0.1)

    def generate(self, text):
        Logger.info("Generating TTS...")
        text = text.replace("\n", " ").strip()
        
        if self.parent.use_bark:
            tts = self.generate_with_bark(text)
        else:
            tts = self.generate_with_t5(text)

        self.add_to_stream_signal.emit(tts)
    
    def move_inputs_to_device(self, inputs):
        if self.parent.use_cuda:
            Logger.info("Moving inputs to CUDA")
            try:
                inputs = {k: v.cuda() for k, v in inputs.items()}
            except AttributeError:
                pass
        return inputs

    def generate_with_bark(self, text):
        Logger.info("Generating TTS...")
        text = text.replace("\n", " ").strip()
        
        Logger.info("Processing inputs...")
        inputs = self.parent.processor(text, voice_preset=self.parent.voice_preset).to(self.parent.device)
        inputs = self.move_inputs_to_device(inputs)

        Logger.info("Generating speech...")
        start = time.time()
        params = dict(
            **inputs, 
            fine_temperature=self.parent.fine_temperature,
            coarse_temperature=self.parent.coarse_temperature,
            semantic_temperature=self.parent.semantic_temperature,
        )
        speech = self.parent.model.generate(**params)
        Logger.info("Generated speech in " + str(time.time() - start) + " seconds")

        tts = speech[0].cpu().float().numpy()
        return tts
    
    def generate_with_t5(self, text):
        Logger.info("Generating TTS...")
        text = text.replace("\n", " ").strip()
        
        Logger.info("Processing inputs...")

        inputs = self.parent.processor(text=text, return_tensors="pt")
        inputs = self.move_inputs_to_device(inputs)

        Logger.info("Generating speech...")
        start = time.time()
        params = dict(
            **inputs,
            speaker_embeddings=self.parent.speaker_embeddings,
            vocoder=self.parent.vocoder,
            max_length=100,
        )
        speech = self.parent.model.generate(**params)
        Logger.info("Generated speech in " + str(time.time() - start) + " seconds")
        tts = speech.cpu().float().numpy()
        return tts


class TTS(QObject):
    character_replacement_map = {
        "\n": " ",
        "’": "'",
        "-": " "
    }
    text_queue = Queue()
    # single_character_sentence_enders = [".", "?", "!", "...", "…"]
    # double_character_sentence_enders = [".”", "?”", "!”", "...”", "…”", ".'", "?'", "!'", "...'", "…'"]
    single_character_sentence_enders = [".", "?", "!", "…"]
    double_character_sentence_enders = [".”", "?”", "!”", "…”", ".'", "?'", "!'", "…'"]
    sentence_delay_time = 1500
    sentence_sample_rate = 20000
    sentence_blocking = True
    buffer_length = 10
    input_text = ""
    buffer = []
    current_sentence = ""
    new_sentence = ""
    tts_sentence = None
    thread_started = False
    is_playing = False
    current_model = None
    do_offload_to_cpu = True
    message = ""
    local_files_only = True

    @property
    def processor_path(self):
        if self.use_bark:
            return "suno/bark-small"
        return "microsoft/speecht5_tts"
    
    @property
    def model_path(self):
        if self.use_bark:
            return "suno/bark-small"
        return "microsoft/speecht5_tts"
    
    @property
    def vocoder_path(self):
        return "microsoft/speecht5_hifigan"
    
    @property
    def speaker_embeddings_dataset_path(self):
        return "Matthijs/cmu-arctic-xvectors"

    @property
    def device(self):
        return f"cuda:{self.cuda_index}" if self.use_cuda else "cpu"

    @property
    def torch_dtype(self):
        return torch.float16 if self.use_cuda else torch.float32

    @property
    def word_chunks(self):
        return self.engine.app.settings["tts_settings"]["word_chunks"]

    @property
    def use_bark(self):
        return self.engine.app.settings["tts_settings"]["use_bark"]

    @property
    def cuda_index(self):
        return self.engine.app.settings["tts_settings"]["cuda_index"]
    
    @property
    def voice_preset(self):
        return self.engine.app.settings["tts_settings"]["voice"]

    @property
    def use_cuda(self):
        return self.engine.app.settings["tts_settings"]["use_cuda"] and torch.cuda.is_available()

    @property
    def fine_temperature(self):
        return self.engine.app.settings["tts_settings"]["fine_temperature"] / 100
    
    @property
    def coarse_temperature(self):
        return self.engine.app.settings["tts_settings"]["coarse_temperature"] / 100
    
    @property
    def semantic_temperature(self):
        return self.engine.app.settings["tts_settings"]["semantic_temperature"] / 100
    
    @property
    def enable_cpu_offload(self):
        return self.engine.app.settings["tts_settings"]["enable_cpu_offload"]
    
    @property
    def play_queue_buffer_length(self):
        return self.engine.app.settings["tts_settings"]["play_queue_buffer_length"]
    
    @property
    def use_word_chunks(self):
        return self.engine.app.settings["tts_settings"]["use_word_chunks"]
    
    @property
    def use_sentence_chunks(self):
        return self.engine.app.settings["tts_settings"]["use_sentence_chunks"]

    @property
    def sentence_chunks(self):
        return self.engine.app.settings["tts_settings"]["sentence_chunks"]

    def __init__(self, *args, **kwargs):
        super().__init__()
        Logger.info("Loading TTS...")
        """
        Initialize the TTS
        """
        self.engine = kwargs.get("engine")
        self.corpus = []
        self.processor = None
        self.model = None
        self.vocoder = None
        self.speaker_embeddings = None
        self.sentences = []

        """
        The vocalizer takes generated speech in the form of numpy arrays and plays them
        using sounddevice. It runs in a separate thread so that we can perform other operations
        while playing speech.
        """
        self.vocalizer = VocalizerWorker(parent=self)
        self.vocalizer_thread = QThread()
        self.vocalizer.moveToThread(self.vocalizer_thread)
        self.vocalizer_thread.started.connect(self.vocalizer.process)
        self.vocalizer_thread.start()
        
        """
        The generator worker takes text from the text queue and generates speech from it.
        It runs in a separate thread so that we can perform other operations while generating
        speech.
        """
        self.generator_worker_thread = QThread()
        self.generator_worker = GeneratorWorker(parent=self)
        self.generator_worker.add_to_stream_signal.connect(self.add_to_stream)
        self.generator_worker.moveToThread(self.generator_worker_thread)
        self.generator_worker_thread.started.connect(self.generator_worker.process)
        self.generator_worker_thread.start()
    
    @pyqtSlot(np.ndarray)
    def add_to_stream(self, generated_speech: np.ndarray):
        """
        This function is called from the generator worker when speech has been generated.
        It adds the generated speech to the vocalizer's queue.
        """
        self.vocalizer.handle_speech(generated_speech)
    
    def move_model(self, to_cpu: bool = False):
        if to_cpu and self.do_offload_to_cpu:
            self.offload_to_cpu()
        else:
            self.move_to_device()
    
    def offload_to_cpu(self):
        """
        Move the model, vocoder, processor and speaker_embeddings to the CPU
        """
        Logger.info("Moving TTS to CPU")
        if self.model:
            self.model = self.model.cpu()
        if self.vocoder:
            self.vocoder = self.vocoder.cpu()
        if self.speaker_embeddings:
            self.speaker_embeddings = self.speaker_embeddings.cpu()
    
    def move_to_device(self):
        """
        Move the model, vocoder, processor and speaker_embeddings to the GPU
        """
        Logger.info("Moving TTS to device")
        if torch.cuda.is_available():
            if self.model:
                self.model = self.model.to(self.device)
            if self.vocoder:
                self.vocoder = self.vocoder.to(self.device)
            if self.speaker_embeddings:
                self.speaker_embeddings = self.speaker_embeddings.to(self.device)

    def initialize(self):
        if not self.engine.app.settings["tts_enabled"]:
            self.unload()
            return

        target_model = "bark" if self.use_bark else "t5"
        if target_model != self.current_model:
            self.unload()
        
        if not self.current_model:
            self.load_model()
            self.load_vocoder()
            self.load_processor()
            self.load_dataset()
            self.load_corpus()
            self.current_model = target_model
    
    def unload(self):
        Logger.info("Unloading TTS")
        do_clear_memory = False
        try:
            del self.model
            do_clear_memory = True
        except AttributeError:
            pass
        try:
            del self.processor
            do_clear_memory = True
        except AttributeError:
            pass
        try:
            del self.vocoder
            do_clear_memory = True
        except AttributeError:
            pass
        try:
            del self.speaker_embeddings
            do_clear_memory = True
        except AttributeError:
            pass
        self.current_model = None
        
        if do_clear_memory:
            self.engine.clear_memory()

    def run(self):
        self.initialize()
        self.process_sentences()

    def load_model(self):
        Logger.info("Loading TTS Model")
        model_class_ = BarkModel if self.use_bark else SpeechT5ForTextToSpeech
        self.model = model_class_.from_pretrained(
            self.model_path, 
            local_files_only=self.local_files_only,
            torch_dtype=self.torch_dtype
        ).to(self.device)

        if self.use_bark:
            self.model = self.model.to_bettertransformer()
            self.model.enable_cpu_offload()
    
    def load_vocoder(self):
        if not self.use_bark:
            Logger.info("Loading TTS Vocoder")
            self.vocoder = SpeechT5HifiGan.from_pretrained(
                self.vocoder_path,
                torch_dtype=self.torch_dtype
            )

            if self.use_cuda:
                self.vocoder = self.vocoder.cuda()
    
    def load_processor(self):
        Logger.info("Loading TTS Procesor")
        processor_class_ = BarkProcessor if self.use_bark else SpeechT5Processor
        self.processor = processor_class_.from_pretrained(self.processor_path)

    def load_dataset(self):
        """
        load xvector containing speaker's voice characteristics from a dataset
        :return:
        """
        if not self.use_bark:
            Logger.info("Loading TTS Dataset")
            embeddings_dataset = load_dataset(self.speaker_embeddings_dataset_path, split="validation")
            self.speaker_embeddings = torch.tensor(embeddings_dataset[7306]["xvector"]).unsqueeze(0)
            
            if self.use_cuda:
                self.speaker_embeddings = self.speaker_embeddings.half().cuda()

    def load_corpus(self):
        if self.input_text:
            corpus = open(self.input_text, "r").read()
            for key, value in self.character_replacement_map.items():
                corpus = corpus.replace(key, value)
            self.corpus = corpus.split(" ")

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
        Logger.info("TTS: Processing sentences")
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

    def add_text(self, text: str, is_end_of_message: bool):
        self.initialize()
        self.message += text
        #if is_end_of_message:
        return self.process_message(is_end_of_message=is_end_of_message)
    
    def process_message(self, is_end_of_message: bool):
        # split on sentence enders
        sentence_enders = self.single_character_sentence_enders + self.double_character_sentence_enders
        
        # split text into words
        words = self.message.split()
        # if not is_end_of_message and len(words) < self.word_chunks:
        #     return False
        
        if self.use_word_chunks:
            # combine words into 30 word chunks
            chunks = [' '.join(words[i:i+self.word_chunks]) for i in range(0, len(words), self.word_chunks)]
            if len(chunks) < 30 and not is_end_of_message:
                return False

            Logger.info("Adding text to TTS queue...")
        
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
                self.text_queue.put(dict(
                    text=chunk,
                    is_end_of_message=is_end_of_message
                ))
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
                    self.text_queue.put(dict(
                        text=chunk,
                        is_end_of_message=is_end_of_message
                    ))
            self.message = ""
        else:            
            self.text_queue.put(dict(
                text=self.message,
                is_end_of_message=is_end_of_message
            ))
            self.message = ""
            
    # def play_buffer(self):
    #     """
    #     now we iterate over each sentence and keep a buffer of 10 sentences. We'll
    #     generate speech for each sentence, and then play the oldest sentence in the
    #     buffer when it fills up. This way we can generate speech for the next sentence
    #     while the current one is playing.
    #     :return:
    #     """
    #     while True:
    #         if len(self.buffer) > 0:
    #             tts = self.buffer.pop(0)
    #             sd.play(
    #                 tts,
    #                 samplerate=self.sentence_sample_rate,
    #                 blocking=self.sentence_blocking
    #             )
    #             time.sleep(self.sentence_delay_time / 1000)