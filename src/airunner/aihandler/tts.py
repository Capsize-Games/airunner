import os
import time
from transformers import SpeechT5Processor, SpeechT5ForTextToSpeech, SpeechT5HifiGan
import torch
import sounddevice as sd
from datasets import load_dataset
import threading
import soundfile as sf
import time
import numpy as np


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
    processor_path = "microsoft/speecht5_tts"
    model_path = "microsoft/speecht5_tts"
    vocoder_path = "microsoft/speecht5_hifigan"
    speaker_embeddings_dataset_path = "Matthijs/cmu-arctic-xvectors"
    buffer = []
    current_sentence = ""

    @property
    def cuda_available(self):
        return torch.cuda.is_available()

    @property
    def device(self):
        return "cuda" if self.cuda_available else "cpu"

    def __init__(self, *args, **kwargs):
        self.corpus = []
        for attr in [
            "character_replacement_map",
            "single_character_sentence_enders",
            "double_character_sentence_enders",
            "sentence_delay_time",
            "sentence_sample_rate",
            "sentence_blocking",
            "buffer_length",
            "input_text",
            "processor_path",
            "model_path",
            "vocoder_path",
            "speaker_embeddings_dataset_path"
        ]:
            val = kwargs.get(attr, getattr(self, attr))
            setattr(self, attr, val)
        self.processor = None
        self.model = None
        self.vocoder = None
        self.speaker_embeddings = None
        self.sentences = []
        # if not self.thread_started:
        #     self.thread_started = True
        #     threading.Thread(target=self.play_buffer).start()
        
        self.stream = sd.OutputStream(samplerate=24000, channels=1)
        self.stream_2 = sd.OutputStream(samplerate=20000, channels=1)
        self.stream.start()
        self.stream_2.start()


    def initialize(self):
        self.load_model()
        self.to_device()
        self.load_dataset()
        self.load_corpus()

    def run(self):
        self.initialize()
        self.process_sentences()
        #self.start_speech_processing()

    def load_model(self):
        self.processor = SpeechT5Processor.from_pretrained(
            self.processor_path,
            # load_in_4bit=True,
        )
        self.model = SpeechT5ForTextToSpeech.from_pretrained(
            self.model_path
        ).half()
        self.vocoder = SpeechT5HifiGan.from_pretrained(
            self.vocoder_path
        ).half()

    def to_device(self):
        self.model = self.model.cuda()
        self.vocoder = self.vocoder.cuda()

    def load_dataset(self):
        """
        load xvector containing speaker's voice characteristics from a dataset
        :return:
        """
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


    new_sentence = ""
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

    def add_sentence(self, sentence, stream):
        self.process_sentence(sentence, stream)
        # self.current_sentence += word
        # # check if self.current_sentence ends with a period
        # if self.current_sentence[-1] in self.single_character_sentence_enders or (
        #     len(self.current_sentence) > 1 and self.current_sentence[-2:] \
        #         in self.double_character_sentence_enders
        # ):
        #     # self.sentences.append(self.current_sentence)
        #     # self.current_sentence = ""
        #     self.process_sentence(self.current_sentence)
        #     self.current_sentence = ""

    def process_speech(self):
        sd.default.blocksize = 4096
        while True:
            if len(self.sentences) > 0:
                self.process_sentence(self.sentences.pop(0))
    
    tts_sentence = None

    def process_sentence(self, text, stream):
        tts_sentence = None
        # add delay to inputs
        text = text.strip() + ". "
        inputs = self.processor(text=text, return_tensors="pt")
        inputs = {k: v.cuda() for k, v in inputs.items()}

        input_ids = inputs["input_ids"]
        # move to cpu
        speech = self.model.generate_speech(
            input_ids,
            self.speaker_embeddings,
            vocoder=self.vocoder
        )
        tts = speech.cpu().float().numpy()
        # if self.tts_sentence is None:
        #     self.tts_sentence = tts
        # else:
        #     self.tts_sentence = np.concatenate((tts_sentence, tts))
        #self.buffer.append(tts_sentence)

        if stream == "a":
            self.stream.write(tts)
        else:
            self.stream_2.write(tts)
        
    
    thread_started = False
    is_playing = False

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

        # save to file
        # check if file exists and append a number to the filename if it does
        # if os.path.exists("sentence.wav"):
        #     i = 1
        #     while os.path.exists(f"sentence{i}.wav"):
        #         i += 1
        #     sf.write(f"sentence{i}.wav", sentence, self.sentence_sample_rate)
        # else:
        #     print("Saving sentence.wav")
        #     sf.write("sentence.wav", sentence, self.sentence_sample_rate)
