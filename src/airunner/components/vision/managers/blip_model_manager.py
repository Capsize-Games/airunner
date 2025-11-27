"""
BLIP-2 Model Manager for image captioning and visual question answering.

Uses Salesforce/blip2-opt-2.7b model with 4-bit quantization for efficient VRAM usage.
"""

import os
from typing import Dict, Optional, Tuple, List, Any

import torch
from PIL import Image

from airunner.components.application.managers.base_model_manager import (
    BaseModelManager,
)
from airunner.enums import ModelType, ModelStatus
from airunner.settings import AIRUNNER_LOCAL_FILES_ONLY
from airunner.utils.application.get_logger import get_logger


class BlipModelManager(BaseModelManager):
    """
    Handler for the BLIP-2 vision-language model.
    
    Supports image captioning and visual question answering using the
    Salesforce/blip2-opt-2.7b model. Uses BitsAndBytes 4-bit quantization
    to minimize VRAM usage (~1.8GB with 4-bit).
    """

    # Default HuggingFace model path
    DEFAULT_MODEL_ID = "Salesforce/blip2-opt-2.7b"

    def __init__(self, *args, **kwargs):
        """Initialize BLIP-2 model manager."""
        self.model_type = ModelType.VISION
        self.model_class = "vision"
        self._model_status = {
            ModelType.VISION: ModelStatus.UNLOADED,
        }
        super().__init__(*args, **kwargs)

        self._model = None
        self._processor = None
        self.logger = get_logger(__name__)

        # Determine device
        self._device = "cuda" if torch.cuda.is_available() else "cpu"

    @property
    def model_path(self) -> str:
        """Get path to the vision model."""
        # Try local path first, fall back to HuggingFace ID
        local_path = os.path.expanduser(
            os.path.join(
                getattr(self, "path_settings", {}).get("base_path", "~/.airunner"),
                "models/vision",
                self.DEFAULT_MODEL_ID.replace("/", "--"),
            )
        )
        if os.path.exists(local_path):
            return local_path
        return self.DEFAULT_MODEL_ID

    @property
    def dtype(self):
        """Get torch dtype based on device."""
        return torch.float16 if torch.cuda.is_available() else torch.float32

    @property
    def vision_is_loading(self) -> bool:
        """Check if vision model is currently loading."""
        return self._model_status.get(ModelType.VISION) is ModelStatus.LOADING

    @property
    def vision_is_loaded(self) -> bool:
        """Check if vision model is loaded."""
        return self._model_status.get(ModelType.VISION) is ModelStatus.LOADED

    @property
    def vision_is_unloaded(self) -> bool:
        """Check if vision model is unloaded."""
        return self._model_status.get(ModelType.VISION) is ModelStatus.UNLOADED

    def load(self) -> bool:
        """
        Load the BLIP-2 model and processor.
        
        Returns:
            True if model loaded successfully, False otherwise.
        """
        if self.vision_is_loading or self.vision_is_loaded:
            return True

        self.logger.debug("Loading BLIP-2 vision model")
        self.change_model_status(ModelType.VISION, ModelStatus.LOADING)

        try:
            self._load_model()
            self._load_processor()

            if self._model is not None and self._processor is not None:
                self.change_model_status(ModelType.VISION, ModelStatus.LOADED)
                self.logger.info("BLIP-2 model loaded successfully")
                return True
            else:
                self.change_model_status(ModelType.VISION, ModelStatus.FAILED)
                self.logger.error("Failed to load BLIP-2 model")
                return False
        except Exception as e:
            self.logger.error(f"Error loading BLIP-2 model: {e}")
            self.change_model_status(ModelType.VISION, ModelStatus.FAILED)
            return False

    def unload(self):
        """Unload the BLIP-2 model and free resources."""
        if self.vision_is_loading or self.vision_is_unloaded:
            return

        self.logger.debug("Unloading BLIP-2 vision model")
        self.change_model_status(ModelType.VISION, ModelStatus.LOADING)

        if self._model is not None:
            del self._model
            self._model = None

        if self._processor is not None:
            del self._processor
            self._processor = None

        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        self.change_model_status(ModelType.VISION, ModelStatus.UNLOADED)
        self.logger.info("BLIP-2 model unloaded")

    def _load_model(self):
        """Load the BLIP-2 model with 4-bit quantization."""
        try:
            from transformers import Blip2ForConditionalGeneration, BitsAndBytesConfig

            # Clean up GPU memory before loading
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            model_path = self.model_path

            # Configure 4-bit quantization if on CUDA
            if torch.cuda.is_available():
                quantization_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_use_double_quant=True,
                    bnb_4bit_quant_type="nf4",
                )
                self._model = Blip2ForConditionalGeneration.from_pretrained(
                    model_path,
                    quantization_config=quantization_config,
                    device_map="auto",
                    torch_dtype=torch.float16,
                    local_files_only=AIRUNNER_LOCAL_FILES_ONLY,
                )
            else:
                # CPU fallback without quantization
                self._model = Blip2ForConditionalGeneration.from_pretrained(
                    model_path,
                    torch_dtype=torch.float32,
                    local_files_only=AIRUNNER_LOCAL_FILES_ONLY,
                )
                self._model = self._model.cpu()

            self.logger.debug(f"Loaded BLIP-2 model from {model_path}")
        except Exception as e:
            self.logger.error(f"Failed to load BLIP-2 model: {e}")
            self._model = None

    def _load_processor(self):
        """Load the BLIP-2 processor."""
        try:
            from transformers import Blip2Processor

            model_path = self.model_path
            self._processor = Blip2Processor.from_pretrained(
                model_path,
                local_files_only=AIRUNNER_LOCAL_FILES_ONLY,
            )
            self.logger.debug(f"Loaded BLIP-2 processor from {model_path}")
        except Exception as e:
            self.logger.error(f"Failed to load BLIP-2 processor: {e}")
            self._processor = None

    def generate_caption(
        self,
        image: Image.Image,
        max_new_tokens: int = 50,
    ) -> str:
        """
        Generate a caption for an image.
        
        Args:
            image: PIL Image to caption.
            max_new_tokens: Maximum number of tokens to generate.
            
        Returns:
            Generated caption string.
        """
        if not self.vision_is_loaded:
            if not self.load():
                return ""

        try:
            # Ensure image is RGB
            if image.mode != "RGB":
                image = image.convert("RGB")

            # Process image
            inputs = self._processor(image, return_tensors="pt")

            # Move inputs to device
            if torch.cuda.is_available():
                inputs = {k: v.to(self._device) for k, v in inputs.items()}

            # Generate caption
            with torch.no_grad():
                generated_ids = self._model.generate(
                    **inputs,
                    max_new_tokens=max_new_tokens,
                )

            # Decode output
            caption = self._processor.batch_decode(
                generated_ids,
                skip_special_tokens=True,
            )[0].strip()

            return caption
        except Exception as e:
            self.logger.error(f"Error generating caption: {e}")
            return ""

    def answer_question(
        self,
        image: Image.Image,
        question: str,
        max_new_tokens: int = 50,
    ) -> str:
        """
        Answer a question about an image (VQA).
        
        Args:
            image: PIL Image to analyze.
            question: Question to answer about the image.
            max_new_tokens: Maximum number of tokens to generate.
            
        Returns:
            Answer string.
        """
        if not self.vision_is_loaded:
            if not self.load():
                return ""

        try:
            # Ensure image is RGB
            if image.mode != "RGB":
                image = image.convert("RGB")

            # Process image with question
            inputs = self._processor(
                image,
                text=question,
                return_tensors="pt",
            )

            # Move inputs to device
            if torch.cuda.is_available():
                inputs = {k: v.to(self._device) for k, v in inputs.items()}

            # Generate answer
            with torch.no_grad():
                generated_ids = self._model.generate(
                    **inputs,
                    max_new_tokens=max_new_tokens,
                )

            # Decode output
            answer = self._processor.batch_decode(
                generated_ids,
                skip_special_tokens=True,
            )[0].strip()

            return answer
        except Exception as e:
            self.logger.error(f"Error answering question: {e}")
            return ""

    def generate_tags(
        self,
        image: Image.Image,
        max_tags: int = 10,
    ) -> List[str]:
        """
        Generate tags for an image.
        
        Uses VQA to extract descriptive tags from the image.
        
        Args:
            image: PIL Image to tag.
            max_tags: Maximum number of tags to generate.
            
        Returns:
            List of tag strings.
        """
        if not self.vision_is_loaded:
            if not self.load():
                return []

        tags = set()

        try:
            # Get main description
            caption = self.generate_caption(image)
            if caption:
                # Extract key nouns/adjectives from caption
                words = caption.lower().replace(".", "").replace(",", "").split()
                # Filter common words
                stop_words = {
                    "a", "an", "the", "is", "are", "of", "in", "on", "at", "to",
                    "and", "or", "with", "this", "that", "it", "its", "there",
                    "has", "have", "from", "for", "by", "as", "be", "was", "were",
                }
                tags.update(w for w in words if w not in stop_words and len(w) > 2)

            # Ask specific questions to get more detailed tags
            questions = [
                "What objects are in this image?",
                "What is the main subject of this image?",
                "What colors are prominent in this image?",
                "What is the setting or location in this image?",
            ]

            for question in questions:
                if len(tags) >= max_tags:
                    break
                answer = self.answer_question(image, question)
                if answer:
                    words = answer.lower().replace(".", "").replace(",", "").split()
                    tags.update(
                        w for w in words 
                        if w not in stop_words and len(w) > 2
                    )

            # Limit and return
            return list(tags)[:max_tags]
        except Exception as e:
            self.logger.error(f"Error generating tags: {e}")
            return []

    def analyze_image(
        self,
        image: Image.Image,
        max_tags: int = 10,
    ) -> Dict[str, Any]:
        """
        Perform full image analysis including caption and tags.
        
        Args:
            image: PIL Image to analyze.
            max_tags: Maximum number of tags to generate.
            
        Returns:
            Dictionary with 'caption' and 'tags' keys.
        """
        result = {
            "caption": "",
            "tags": [],
        }

        if not self.vision_is_loaded:
            if not self.load():
                return result

        try:
            # Generate caption
            result["caption"] = self.generate_caption(image)

            # Generate tags
            result["tags"] = self.generate_tags(image, max_tags)

            return result
        except Exception as e:
            self.logger.error(f"Error analyzing image: {e}")
            return result
