"""
Vision endpoints for image captioning, tagging, and analysis.

Uses Qwen2-VL model for image understanding tasks.
"""

import base64
import io
import os
import re
from typing import Optional, List

import torch
from PIL import Image
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger

logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)
router = APIRouter()

# Global model state
_model = None
_processor = None
_device = None


# ====================
# Pydantic Models
# ====================


class ImageRequest(BaseModel):
    """Base image request."""
    image: str  # base64-encoded image
    max_tokens: int = 100


class CaptionRequest(ImageRequest):
    """Caption generation request."""
    pass


class TagRequest(BaseModel):
    """Tag generation request."""
    image: str  # base64-encoded image
    max_tags: int = 10


class AnalyzeRequest(BaseModel):
    """Full analysis request."""
    image: str  # base64-encoded image
    max_tags: int = 10


class VQARequest(BaseModel):
    """Visual Question Answering request."""
    image: str  # base64-encoded image
    question: str
    max_tokens: int = 100


class CaptionResponse(BaseModel):
    """Caption response."""
    caption: str


class TagResponse(BaseModel):
    """Tag response."""
    tags: List[str]


class AnalyzeResponse(BaseModel):
    """Full analysis response."""
    caption: str
    tags: List[str]


class VQAResponse(BaseModel):
    """VQA response."""
    answer: str


# ====================
# Model Loading
# ====================


def load_vision_model():
    """Load the Qwen2-VL model for vision tasks."""
    global _model, _processor, _device

    if _model is not None:
        return

    logger.info("Loading Qwen2-VL model for vision tasks...")

    from transformers import Qwen2VLForConditionalGeneration, AutoProcessor

    model_name = os.environ.get("VISION_MODEL", "Qwen/Qwen2-VL-2B-Instruct")

    _device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info(f"Vision model using device: {_device}")

    _processor = AutoProcessor.from_pretrained(model_name, trust_remote_code=True)

    if _device == "cuda":
        _model = Qwen2VLForConditionalGeneration.from_pretrained(
            model_name,
            torch_dtype=torch.float16,
            device_map="auto",
            trust_remote_code=True,
        )
    else:
        _model = Qwen2VLForConditionalGeneration.from_pretrained(
            model_name,
            torch_dtype=torch.float32,
            trust_remote_code=True,
        ).to(_device)

    logger.info("Vision model loaded successfully")


def decode_image(image_b64: str) -> Image.Image:
    """Decode base64 image to PIL Image."""
    try:
        image_data = base64.b64decode(image_b64)
        return Image.open(io.BytesIO(image_data)).convert("RGB")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image: {e}")


def generate_vision_response(image: Image.Image, prompt: str, max_tokens: int = 100) -> str:
    """Generate a response from the vision model."""
    global _model, _processor, _device

    if _model is None:
        load_vision_model()

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image", "image": image},
                {"type": "text", "text": prompt},
            ],
        }
    ]

    text = _processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)

    inputs = _processor(
        text=[text],
        images=[image],
        padding=True,
        return_tensors="pt",
    ).to(_device)

    with torch.no_grad():
        generated_ids = _model.generate(
            **inputs,
            max_new_tokens=max_tokens,
            do_sample=True,
            temperature=0.7,
        )

    # Decode only new tokens
    generated_ids_trimmed = [
        out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
    ]

    output = _processor.batch_decode(
        generated_ids_trimmed,
        skip_special_tokens=True,
        clean_up_tokenization_spaces=False,
    )[0]

    return output.strip()


# ====================
# API Endpoints
# ====================


@router.post("/caption", response_model=CaptionResponse)
async def caption_image(request: CaptionRequest):
    """
    Generate a caption for an image.

    Args:
        request: CaptionRequest with base64-encoded image

    Returns:
        CaptionResponse with generated caption
    """
    logger.info("Caption request received")
    image = decode_image(request.image)

    prompt = "Describe this image in a single concise sentence."
    caption = generate_vision_response(image, prompt, request.max_tokens)

    return CaptionResponse(caption=caption)


@router.post("/tags", response_model=TagResponse)
async def tag_image(request: TagRequest):
    """
    Generate tags for an image.

    Args:
        request: TagRequest with base64-encoded image

    Returns:
        TagResponse with list of tags
    """
    logger.info("Tag request received")
    image = decode_image(request.image)

    prompt = f"""List up to {request.max_tags} descriptive tags for this image.
Return ONLY a comma-separated list of single-word or short-phrase tags.
Example: nature, sunset, mountains, scenic, peaceful
Tags:"""

    response = generate_vision_response(image, prompt, max_tokens=100)

    # Parse tags from response
    tags = []
    for tag in response.split(","):
        tag = tag.strip().lower()
        # Clean up tag
        tag = re.sub(r'[^\w\s-]', '', tag)
        if tag and len(tag) > 1 and len(tag) < 50:
            tags.append(tag)

    return TagResponse(tags=tags[:request.max_tags])


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_image(request: AnalyzeRequest):
    """
    Full image analysis: caption + tags.

    Args:
        request: AnalyzeRequest with base64-encoded image

    Returns:
        AnalyzeResponse with caption and tags
    """
    logger.info("Analyze request received")
    image = decode_image(request.image)

    # Generate caption
    caption_prompt = "Describe this image in a single concise sentence."
    caption = generate_vision_response(image, caption_prompt, max_tokens=50)

    # Generate tags
    tags_prompt = f"""List up to {request.max_tags} descriptive tags for this image.
Return ONLY a comma-separated list of single-word or short-phrase tags.
Tags:"""

    tags_response = generate_vision_response(image, tags_prompt, max_tokens=100)

    # Parse tags
    tags = []
    for tag in tags_response.split(","):
        tag = tag.strip().lower()
        tag = re.sub(r'[^\w\s-]', '', tag)
        if tag and len(tag) > 1 and len(tag) < 50:
            tags.append(tag)

    return AnalyzeResponse(
        caption=caption,
        tags=tags[:request.max_tags],
    )


@router.post("/vqa", response_model=VQAResponse)
async def vqa(request: VQARequest):
    """
    Visual Question Answering.

    Args:
        request: VQARequest with base64-encoded image and question

    Returns:
        VQAResponse with answer
    """
    logger.info(f"VQA request: {request.question[:50]}...")
    image = decode_image(request.image)
    answer = generate_vision_response(image, request.question, request.max_tokens)
    return VQAResponse(answer=answer)
