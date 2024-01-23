import time

from airunner.workers.worker import Worker
from airunner.aihandler.tts import TTS


class TTSGeneratorWorker(Worker):
    """
    Takes input text from any source and generates speech from it using the TTS class.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tts = TTS()
        self.tts.run()
        self.play_queue = []
        self.play_queue_started = False
        
    def handle_message(self, data):
        message = data["message"]
        #play_queue_buffer_length = self.tts_settings["play_queue_buffer_length"]
        self.play_queue.append(message)
        if data["is_end_of_message"] or len(self.play_queue) >= 15:
            # for item in self.play_queue:
            #     self.generate(item)
            # self.play_queue = []
            # if is_end_of_message or len(self.play_queue) == play_queue_buffer_length or self.play_queue_started:
            #     self.play_queue_started = True
            #     self.generate(message)
            sentence = " ".join(self.play_queue).strip()
            self.logger.debug(f"Generating TTS for sentence {sentence}")
            self.generate(sentence)
            self.play_queue_started = True
            self.play_queue = []

    def generate(self, message):
        self.logger.info("Generating TTS...")
        self.logger.info(message)
        if type(message) == dict:
            message = message.get("message", "")
        text = message.replace("\n", " ").strip()

        if text == "":
            return
        
        self.logger.info(f"Generating TTS with {text}")
        
        if self.tts_settings["use_bark"]:
            response = self.generate_with_bark(text)
        else:
            response = self.generate_with_t5(text)

        print("adding to stream", response)
        self.emit("TTSGeneratorWorker_add_to_stream_signal", response)
    
    def move_inputs_to_device(self, inputs):
        use_cuda = self.tts_settings["use_cuda"]
        if use_cuda:
            self.logger.info("Moving inputs to CUDA")
            try:
                inputs = {k: v.cuda() for k, v in inputs.items()}
            except AttributeError:
                pass
        return inputs

    def generate_with_bark(self, text):
        self.logger.info("Generating TTS...")
        text = text.replace("\n", " ").strip()
        
        self.logger.info("Processing inputs...")
        inputs = self.tts.processor(text, voice_preset=self.tts_settings["voice"]).to(self.tts.device)
        inputs = self.move_inputs_to_device(inputs)

        self.logger.info("Generating speech...")
        start = time.time()
        params = dict(
            **inputs, 
            fine_temperature=self.tts_settings["fine_temperature"],
            coarse_temperature=self.tts_settings["coarse_temperature"],
            semantic_temperature=self.tts_settings["semantic_temperature"],
        )
        speech = self.tts.model.generate(**params)
        self.logger.info("Generated speech in " + str(time.time() - start) + " seconds")

        response = speech[0].cpu().float().numpy()
        return response
    
    def generate_with_t5(self, text):
        self.logger.info("Generating TTS...")
        text = text.replace("\n", " ").strip()
        
        self.logger.info("Processing inputs...")

        inputs = self.tts.processor(text=text, return_tensors="pt")
        inputs = self.move_inputs_to_device(inputs)

        self.logger.info("Generating speech...")
        start = time.time()
        params = dict(
            **inputs,
            speaker_embeddings=self.tts.speaker_embeddings,
            vocoder=self.tts.vocoder,
            max_length=100,
        )
        speech = self.tts.model.generate(**params)
        self.logger.info("Generated speech in " + str(time.time() - start) + " seconds")
        response = speech.cpu().float().numpy()
        return response
