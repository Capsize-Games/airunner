from transformers import (
    BlipForQuestionAnswering,
    AutoProcessor
)
from airunner.aihandler.llm.transformer_base_handler import TransformerBaseHandler
from airunner.utils.clear_memory import clear_memory


class VisualQATransformerBaseHandler(TransformerBaseHandler):
    """
    Visual QA Transformer Base Handler.
    Uses a processor and model to generate information about a given image.
    """
    auto_class_ = BlipForQuestionAnswering

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.prompt = "This is an image of"
        self.model_path = self.settings["ocr_settings"]["model_path"]
        self.processor = None
        self.do_sample = False
        self.num_beams = 1
        # self.max_length = 256
        self.min_length = 1
        self.top_p = 1.0
        self.repetition_penalty = 1.0
        self.length_penalty = 1.0
        self.temperature = 0.9
        self.processed_vision_history = []
        self.use_saved_model = False

    def post_load(self):
        do_load_processor = self.processor is None
        if do_load_processor:
            self.load_processor()

    def load_processor(self):
        self.logger.debug(f"Loading processor {self.model_path}")
        kwargs = {
            'local_files_only': True,
            'trust_remote_code': True,

        }
        if self.do_quantize_model:
            config = self.quantization_config()
            if config:
                kwargs["quantization_config"] = config
        else:
            kwargs["torch_dtype"] = self.torch_dtype
            if self.use_cuda:
                kwargs["device"] = self.device

        try:
            self.processor = AutoProcessor.from_pretrained(
                self.model_path,
                **kwargs
            )
        except OSError as _e:
            self.logger.error("Failed to load processor")
            return False
        if self.processor:
            self.logger.debug("Processor loaded")
        else:
            self.logger.error("Failed to load processor")

    def unload_processor(self):
        self.logger.debug("Unloading processor")
        if self.processor:
            self.processor = None
            return True

    def unload(self):
        super().unload()
        if (
            self.unload_processor()
        ):
            clear_memory()

    def process_data(self, data):
        super().process_data(data)
        self.image = self.request_data.get("image")

    def do_generate(self) -> str:
        image = self.image.convert("RGB")
        inputs = self.processor(
            images=image,
            text="What is happening in this image?",
            return_tensors="pt"
        )
        # inputs = self.processor("This is an image of", [image], self.model, max_crops=100, num_tokens=728)

        if self.use_cuda:
            inputs = inputs.to(self.device)

        try:
            out = self.model.generate(
                **inputs,
                do_sample=self.do_sample,
                num_beams=self.num_beams,
                # max_length=self.max_length,
                min_length=self.min_length,
                top_p=self.top_p,
                repetition_penalty=self.repetition_penalty,
                length_penalty=self.length_penalty,
                temperature=self.temperature,
            )
        except AttributeError as e:
            return ""

        try:
            generated_text = self.processor.batch_decode(
                out, skip_special_tokens=True
            )[0].strip()
            self.processed_vision_history.append(generated_text)
            return generated_text
        except AttributeError as e:
            return ""

    def prepare_input_args(self):
        kwargs = super().prepare_input_args()
        for key in ["return_result", "skip_special_tokens", "seed"]:
            kwargs.pop(key)
        return kwargs

    def model_params(self) -> dict:
        params = super().model_params()
        del params["use_cache"]
        return params
