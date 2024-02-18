import torch
from transformers import BlipForConditionalGeneration, BlipProcessor
from airunner.aihandler.llm.transformer_base_handler import TransformerBaseHandler
from airunner.utils import clear_memory


class VisualQATransformerBaseHandler(TransformerBaseHandler):
    """
    Visual QA Transformer Base Handler.
    Uses a processor and model to generate information about a given image.
    """
    auto_class_ = BlipForConditionalGeneration

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.prompt = "This is an image of"
        self.model_path = "Salesforce/blip-image-captioning-large"
        self.processor = None
        self.do_sample = False
        self.num_beams = 5
        self.max_length = 256
        self.min_length = 1
        self.top_p = 0.9
        self.repetition_penalty = 1.5
        self.length_penalty = 1.0
        self.temperature = 1
        self.vision_history = []
        self.processed_vision_history = []

    def post_load(self):
        do_load_processor = self.processor is None
        if do_load_processor:
            self.load_processor()

    def load_processor(self, local_files_only=None):
        self.logger.info(f"Loading processor {self.model_path}")
        kwargs = {
            'device_map': 'auto',
            'torch_dtype': torch.float16,
            'local_files_only': self.local_files_only if local_files_only is None else local_files_only,
        }
        config = self.quantization_config()
        if config:
            kwargs["quantization_config"] = config
        self.processor = BlipProcessor.from_pretrained(
            self.model_path,
            **kwargs
        )
        if self.processor:
            self.logger.info("Processor loaded")
        else:
            self.logger.error("Failed to load processor")

    def unload_processor(self):
        self.logger.info("Unloading processor")
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
        self.vision_history.append(self.image)

    def do_generate(self) -> str:
        image = self.image.convert("RGB")
        inputs = self.processor(
            images=image,
            text="This is an image of",
            return_tensors="pt"
        ).to("cuda")

        try:
            out = self.model.generate(
                **inputs,
                do_sample=self.do_sample,
                num_beams=self.num_beams,
                max_length=self.max_length,
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

    def model_params(self, local_files_only) -> dict:
        params = super().model_params(local_files_only)
        del params["use_cache"]
        return params
