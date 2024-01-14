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
                if started:
                    self.stream.write(item)
                else:
                    data.append(item)

                if not started and len(data) >= 6:
                    for item in data:
                        self.stream.write(item)
                    started = True
                    data = []
            except Empty:
                continue
        
    def handle_speech(self, generated_speech):
        print("ADD TO QUEUE")
        Logger.info("Adding speech to stream...")
        try:
            print("Writing speech to stream...")
            self.queue.put(generated_speech)
            print("Successfully added")
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
        while True:
            if not self.parent.text_queue.empty():
                text = self.parent.text_queue.get()
                self.generate(text)
            time.sleep(0.1)

    def generate(self, text):
        Logger.info("Generating TTS...")
        if self.parent.use_bark:
            Logger.info("Using voice preset " + self.parent.voice_preset)
            inputs = self.parent.processor(text, voice_preset=self.parent.voice_preset).to(self.parent.device)
        else:
            Logger.info("We aren't using bark...")
            inputs = self.parent.processor(text=text, return_tensors="pt")
            inputs = {k: v.cuda() for k, v in inputs.items()}

        input_ids = inputs["input_ids"]
        # move to cpu
        if not self.parent.use_bark:
            Logger.info("We still are not using bark...")
            speech = self.parent.model.generate_speech(
                input_ids,
                self.parent.speaker_embeddings,
                vocoder=self.parent.vocoder
            )
            tts = speech.cpu().float().numpy()
        else:
            # track the time it takes to generate speech
            Logger.info("Generating speech...")
            start = time.time()
            speech = self.parent.model.generate(
                **inputs, 
                do_sample=True, 
                fine_temperature=0.4, 
                coarse_temperature=0.8
            )
            Logger.info("Generated speech in " + str(time.time() - start) + " seconds")
            start = time.time()
            tts = speech[0].cpu().float().numpy()
            Logger.info("Converted speech to numpy array in " + str(time.time() - start) + " seconds")
        self.add_to_stream_signal.emit(tts)


class TTS(QObject):
    character_replacement_map = {
        "\n": " ",
        "’": "'",
        "-": " "
    }
    text_queue = Queue()
    single_character_sentence_enders = [".", "?", "!", "...", "…"]
    double_character_sentence_enders = [".”", "?”", "!”", "...”", "…”", ".'", "?'", "!'", "...'", "…'"]
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
        return "cuda:0" if torch.cuda.is_available() else "cpu"
    
    @property
    def model_class_(self):
        if self.use_bark:
            return BarkModel
        return SpeechT5ForTextToSpeech
    
    @property
    def processor_class_(self):
        if self.use_bark:
            return BarkProcessor
        return SpeechT5Processor

    def __init__(self, *args, **kwargs):
        super().__init__()
        Logger.info("Loading TTS...")
        """
        Initialize the TTS
        """
        self.engine = kwargs.get("engine")
        self.use_bark = kwargs.get("use_bark")
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
        print("add_to_stream called")
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
        if self.current_model and self.current_model == "bark" and not self.use_bark:
            self.unload_model()
        
        if not self.current_model:
            self.load_model()
            self.load_vocoder()
            self.load_processor()
            self.load_dataset()
            self.load_corpus()
            self.current_model = "bark" if self.use_bark else "t5"
    
    def unload_model(self):
        del self.model
        del self.processor
        del self.vocoder
        del self.speaker_embeddings
        self.current_model = None
        self.engine.clear_memory()

    def run(self):
        self.initialize()
        self.process_sentences()

    def load_model(self):
        model = self.model_class_.from_pretrained(
            self.model_path, 
            torch_dtype=torch.float16
        ).to(self.device)
        self.model = model.to_bettertransformer()
        # self.model.enable_cpu_offload()
    
    def load_vocoder(self):
        if not self.use_bark:
            self.vocoder = SpeechT5HifiGan.from_pretrained(self.vocoder_path).half().to(self.device)
    
    def load_processor(self):
        self.processor = self.processor_class_.from_pretrained(self.processor_path)

    def load_dataset(self):
        """
        load xvector containing speaker's voice characteristics from a dataset
        :return:
        """
        if not self.use_bark:
            embeddings_dataset = load_dataset(self.speaker_embeddings_dataset_path, split="validation")
            self.speaker_embeddings = torch.tensor(embeddings_dataset[7306]["xvector"]).unsqueeze(0)
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

    # def start_speech_processing(self):
    #     threading.Thread(target=self.process_speech).start()

    def add_word(self, word, stream):
        self.new_sentence += word
        # check if sentence ends with a period, comma, question mark, exclamation point, or ellipsis
        if len(self.new_sentence) > 1 and self.new_sentence[-1] in self.single_character_sentence_enders or (
            len(self.new_sentence) > 1 and self.new_sentence.strip()[-1:] in self.double_character_sentence_enders
        ):
            self.add_sentence(self.new_sentence, stream)
            self.new_sentence = ""

    def add_sentence(self, sentence, stream, tts_settings):
        self.use_bark = tts_settings["use_bark"]
        self.voice_preset = tts_settings["voice"]
        return self.process_sentence(sentence, stream)

    # def process_speech(self):
    #     sd.default.blocksize = 4096
    #     while True:
    #         if len(self.sentences) > 0:
    #             self.process_sentence(self.sentences.pop(0))
    
    def process_sentence(self, text, stream):
        # split on sentence enders
        sentence_enders = self.single_character_sentence_enders + self.double_character_sentence_enders
        
        # split text into sentences
        sentences = []
        current_sentence = ""
        for char in text:
            current_sentence += char
            if char in sentence_enders:
                sentences.append(current_sentence)
                current_sentence = ""

        if current_sentence != "":
            sentences.append(current_sentence)

        for text in sentences:
            # add delay to inputs
            text = text.strip()
            if text.startswith("\n") or text.startswith(" "):
                text = text[1:]
            if text.endswith("\n") or text.endswith(" "):
                text = text[:-1]            
            self.text_queue.put(text)
            yield True
            
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
