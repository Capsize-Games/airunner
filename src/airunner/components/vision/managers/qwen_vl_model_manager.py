"""
Qwen2.5-VL Model Manager for image captioning and visual question answering.

Uses Qwen/Qwen2.5-VL-7B-Instruct model with 4-bit quantization for efficient VRAM usage.
This is the state-of-the-art vision-language model as of late 2024, significantly
outperforming older models like BLIP-2 on all benchmarks.

Memory Usage:
- FP16: ~16GB VRAM
- 4-bit quantized: ~5-6GB VRAM (recommended)
- With Flash Attention 2: Additional memory savings

Features:
- State-of-the-art performance on DocVQA, TextVQA, RealWorldQA, OCRBench
- Dynamic resolution handling (any image size)
- Excellent OCR and text reading capabilities
- Multilingual support
"""

import os
from typing import Dict, Optional, List, Any

import torch
from PIL import Image

from airunner.components.application.managers.base_model_manager import (
    BaseModelManager,
)
from airunner.enums import ModelType, ModelStatus
from airunner.settings import AIRUNNER_LOCAL_FILES_ONLY
from airunner.utils.application.get_logger import get_logger


class QwenVLModelManager(BaseModelManager):
    """
    Handler for the Qwen2.5-VL vision-language model.
    
    Supports image captioning and visual question answering using the
    Qwen/Qwen2.5-VL-7B-Instruct model. Uses BitsAndBytes 4-bit quantization
    to minimize VRAM usage (~5-6GB with 4-bit).
    """

    # Default HuggingFace model path
    DEFAULT_MODEL_ID = "Qwen/Qwen2.5-VL-7B-Instruct"

    def __init__(self, *args, **kwargs):
        """Initialize Qwen2.5-VL model manager."""
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
        
        # Image resolution limits for memory management
        # 256-1280 tokens is a good balance of quality and memory
        self._min_pixels = 256 * 28 * 28  # ~200k pixels
        self._max_pixels = 1280 * 28 * 28  # ~1M pixels

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
        return torch.bfloat16 if torch.cuda.is_available() else torch.float32

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
        Load the Qwen2.5-VL model and processor.
        
        Returns:
            True if model loaded successfully, False otherwise.
        """
        if self.vision_is_loading or self.vision_is_loaded:
            return True

        self.logger.debug("Loading Qwen2.5-VL vision model")
        self.change_model_status(ModelType.VISION, ModelStatus.LOADING)

        try:
            self._load_model()
            self._load_processor()

            if self._model is not None and self._processor is not None:
                self.change_model_status(ModelType.VISION, ModelStatus.LOADED)
                self.logger.info("Qwen2.5-VL model loaded successfully")
                return True
            else:
                self.change_model_status(ModelType.VISION, ModelStatus.FAILED)
                self.logger.error("Failed to load Qwen2.5-VL model")
                return False
        except Exception as e:
            self.logger.error(f"Error loading Qwen2.5-VL model: {e}")
            self.change_model_status(ModelType.VISION, ModelStatus.FAILED)
            return False

    def unload(self):
        """Unload the Qwen2.5-VL model and free resources."""
        if self.vision_is_loading or self.vision_is_unloaded:
            return

        self.logger.debug("Unloading Qwen2.5-VL vision model")
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
        self.logger.info("Qwen2.5-VL model unloaded")

    def _load_model(self):
        """Load the Qwen2.5-VL model with 4-bit quantization."""
        try:
            from transformers import Qwen2VLForConditionalGeneration, BitsAndBytesConfig

            # Clean up GPU memory before loading
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            model_path = self.model_path

            # Configure 4-bit quantization if on CUDA
            if torch.cuda.is_available():
                quantization_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.bfloat16,
                    bnb_4bit_use_double_quant=True,
                    bnb_4bit_quant_type="nf4",
                )
                
                # Try to use Flash Attention 2 for additional memory savings
                try:
                    self._model = Qwen2VLForConditionalGeneration.from_pretrained(
                        model_path,
                        quantization_config=quantization_config,
                        device_map="auto",
                        torch_dtype=torch.bfloat16,
                        attn_implementation="flash_attention_2",
                        local_files_only=AIRUNNER_LOCAL_FILES_ONLY,
                    )
                    self.logger.info("Loaded with Flash Attention 2")
                except Exception as fa_error:
                    self.logger.warning(f"Flash Attention 2 not available: {fa_error}")
                    self._model = Qwen2VLForConditionalGeneration.from_pretrained(
                        model_path,
                        quantization_config=quantization_config,
                        device_map="auto",
                        torch_dtype=torch.bfloat16,
                        local_files_only=AIRUNNER_LOCAL_FILES_ONLY,
                    )
            else:
                # CPU fallback without quantization
                self._model = Qwen2VLForConditionalGeneration.from_pretrained(
                    model_path,
                    torch_dtype=torch.float32,
                    local_files_only=AIRUNNER_LOCAL_FILES_ONLY,
                )
                self._model = self._model.cpu()

            self.logger.debug(f"Loaded Qwen2.5-VL model from {model_path}")
        except Exception as e:
            self.logger.error(f"Failed to load Qwen2.5-VL model: {e}")
            self._model = None

    def _load_processor(self):
        """Load the Qwen2.5-VL processor with memory-optimized settings."""
        try:
            from transformers import AutoProcessor

            model_path = self.model_path
            
            # Configure processor with resolution limits for memory management
            self._processor = AutoProcessor.from_pretrained(
                model_path,
                min_pixels=self._min_pixels,
                max_pixels=self._max_pixels,
                local_files_only=AIRUNNER_LOCAL_FILES_ONLY,
            )
            self.logger.debug(f"Loaded Qwen2.5-VL processor from {model_path}")
        except Exception as e:
            self.logger.error(f"Failed to load Qwen2.5-VL processor: {e}")
            self._processor = None

    def _prepare_messages(self, image: Image.Image, prompt: str) -> list:
        """Prepare message format for Qwen2.5-VL."""
        return [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": prompt},
                ],
            }
        ]

    def _generate(
        self,
        image: Image.Image,
        prompt: str,
        max_new_tokens: int = 128,
    ) -> str:
        """
        Internal generation method.
        
        Args:
            image: PIL Image to process.
            prompt: Text prompt for the model.
            max_new_tokens: Maximum tokens to generate.
            
        Returns:
            Generated text string.
        """
        if not self.vision_is_loaded:
            if not self.load():
                return ""

        try:
            # Ensure image is RGB
            if image.mode != "RGB":
                image = image.convert("RGB")

            # Prepare messages
            messages = self._prepare_messages(image, prompt)

            # Apply chat template
            text = self._processor.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )

            # Process inputs
            from qwen_vl_utils import process_vision_info
            image_inputs, video_inputs = process_vision_info(messages)
            
            inputs = self._processor(
                text=[text],
                images=image_inputs,
                videos=video_inputs,
                padding=True,
                return_tensors="pt",
            )
            
            if torch.cuda.is_available():
                inputs = inputs.to("cuda")

            # Generate
            with torch.no_grad():
                generated_ids = self._model.generate(
                    **inputs,
                    max_new_tokens=max_new_tokens,
                    do_sample=False,
                )

            # Decode - trim input tokens
            generated_ids_trimmed = [
                out_ids[len(in_ids):]
                for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
            ]
            
            output = self._processor.batch_decode(
                generated_ids_trimmed,
                skip_special_tokens=True,
                clean_up_tokenization_spaces=False,
            )[0].strip()

            return output
        except ImportError:
            # Fallback without qwen_vl_utils
            return self._generate_simple(image, prompt, max_new_tokens)
        except Exception as e:
            self.logger.error(f"Error generating: {e}")
            return ""

    def _generate_simple(
        self,
        image: Image.Image,
        prompt: str,
        max_new_tokens: int = 128,
    ) -> str:
        """Simplified generation without qwen_vl_utils."""
        try:
            # Ensure image is RGB
            if image.mode != "RGB":
                image = image.convert("RGB")

            # Simple processing
            inputs = self._processor(
                text=prompt,
                images=image,
                return_tensors="pt",
            )
            
            if torch.cuda.is_available():
                inputs = inputs.to("cuda")

            with torch.no_grad():
                generated_ids = self._model.generate(
                    **inputs,
                    max_new_tokens=max_new_tokens,
                    do_sample=False,
                )

            output = self._processor.batch_decode(
                generated_ids,
                skip_special_tokens=True,
            )[0].strip()

            return output
        except Exception as e:
            self.logger.error(f"Error in simple generation: {e}")
            return ""

    def generate_caption(
        self,
        image: Image.Image,
        max_new_tokens: int = 100,
    ) -> str:
        """
        Generate a caption for an image.
        
        Args:
            image: PIL Image to caption.
            max_new_tokens: Maximum number of tokens to generate.
            
        Returns:
            Generated caption string.
        """
        prompt = "Describe this image in detail. Focus on the main subjects, objects, colors, and setting."
        return self._generate(image, prompt, max_new_tokens)

    def answer_question(
        self,
        image: Image.Image,
        question: str,
        max_new_tokens: int = 100,
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
        return self._generate(image, question, max_new_tokens)

    def generate_tags(
        self,
        image: Image.Image,
        max_tags: int = 15,
    ) -> List[str]:
        """
        Generate tags for an image.
        
        Args:
            image: PIL Image to tag.
            max_tags: Maximum number of tags to generate.
            
        Returns:
            List of tag strings.
        """
        prompt = f"""List up to {max_tags} descriptive tags for this image. 
Include: main subjects, objects, colors, style, mood, and setting.
Output only the tags as a comma-separated list, nothing else."""

        response = self._generate(image, prompt, max_new_tokens=150)
        
        if not response:
            return []
        
        # Parse comma-separated tags
        tags = []
        for tag in response.split(","):
            tag = tag.strip().lower()
            # Clean up common prefixes/suffixes
            tag = tag.strip(".-•*123456789() ")
            if tag and len(tag) > 1 and len(tag) < 50:
                tags.append(tag)
        
        return tags[:max_tags]

    def analyze_image(
        self,
        image: Image.Image,
        max_tags: int = 15,
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

    def read_text(
        self,
        image: Image.Image,
    ) -> str:
        """
        Extract text from an image (OCR).
        
        Qwen2.5-VL has excellent OCR capabilities.
        
        Args:
            image: PIL Image containing text.
            
        Returns:
            Extracted text string.
        """
        prompt = "Read and transcribe all text visible in this image. Output only the text, preserving the layout as much as possible."
        return self._generate(image, prompt, max_new_tokens=500)
