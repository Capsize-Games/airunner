import time
import torch
import sounddevice as sd
import threading

from transformers import SpeechT5Processor, SpeechT5ForTextToSpeech, SpeechT5HifiGan, BarkModel, BarkProcessor

from datasets import load_dataset

from airunner.aihandler.logger import Logger


class TTS:
    character_replacement_map = {
        "\n": " ",
        "’": "'",
        "-": " "
    }
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
        Logger.info("Loading Text To Speech stream...")
        self.engine = kwargs.get("engine")
        self.use_bark = kwargs.get("use_bark")
        self.corpus = []
        self.processor = None
        self.model = None
        self.vocoder = None
        self.speaker_embeddings = None
        self.sentences = []
        
        self.stream = sd.OutputStream(samplerate=24000, channels=1)
        self.stream_2 = sd.OutputStream(samplerate=20000, channels=1)
        self.stream.start()
        self.stream_2.start()
    
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
        #self.model.enable_cpu_offload()
    
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
                self.sentences.append(sentence)
                sentence = ""
        if sentence != "":
            self.sentences.append(sentence)

    def start_speech_processing(self):
        threading.Thread(target=self.process_speech).start()

    def add_word(self, word, stream):
        self.new_sentence += word
        # check if sentence ends with a period, comma, question mark, exclamation point, or ellipsis
        if len(self.new_sentence) > 1 and self.new_sentence[-1] in self.single_character_sentence_enders or (
            len(self.new_sentence) > 1 and self.new_sentence.strip()[-1:] in self.double_character_sentence_enders
        ):
            # remove John: or Jane: from start of sentence of it exists
            if self.new_sentence.startswith(" John: ") or self.new_sentence.startswith(" Jane: "):
                self.new_sentence = self.new_sentence.split(": ")[1]
            if self.new_sentence.startswith(" John: ") or self.new_sentence.startswith(" Jane: "):
                self.new_sentence = self.new_sentence.split(": ")[1]
            self.add_sentence(self.new_sentence, stream)
            self.new_sentence = ""

    def add_sentence(self, sentence, stream, tts_settings):
        self.use_bark = tts_settings["use_bark"]
        self.voice_preset = tts_settings["voice"]
        return self.process_sentence(sentence, stream)

    def process_speech(self):
        sd.default.blocksize = 4096
        while True:
            if len(self.sentences) > 0:
                self.process_sentence(self.sentences.pop(0))
    
    def process_sentence(self, text, stream):
        # add delay to inputs
        text = text.strip()
        if text.startswith("\n") or text.startswith(" "):
            text = text[1:]
        if text.endswith("\n") or text.endswith(" "):
            text = text[:-1]
        print("GENERATING TTS FOR ", text)
        
        if self.use_bark:
            Logger.info("Using voice preset " + self.voice_preset)
            inputs = self.processor(text, voice_preset=self.voice_preset).to(self.device)
        else:
            inputs = self.processor(text=text, return_tensors="pt")
            inputs = {k: v.cuda() for k, v in inputs.items()}

        input_ids = inputs["input_ids"]
        # move to cpu
        if not self.use_bark:
            speech = self.model.generate_speech(
                input_ids,
                self.speaker_embeddings,
                vocoder=self.vocoder
            )
            tts = speech.cpu().float().numpy()
        else:
            speech = self.model.generate(
                **inputs, 
                do_sample=True, 
                fine_temperature=0.4, 
                coarse_temperature=0.8
            )
            tts = speech[0].cpu().float().numpy()
        
        yield True

        if stream == "a":
            self.stream.write(tts)
        else:
            self.stream_2.write(tts)
            
    def play_buffer(self):
        """
        now we iterate over each sentence and keep a buffer of 10 sentences. We'll
        generate speech for each sentence, and then play the oldest sentence in the
        buffer when it fills up. This way we can generate speech for the next sentence
        while the current one is playing.
        :return:
        """
        while True:
            if len(self.buffer) > 0:
                tts = self.buffer.pop(0)
                sd.play(
                    tts,
                    samplerate=self.sentence_sample_rate,
                    blocking=self.sentence_blocking
                )
                time.sleep(self.sentence_delay_time / 1000)
