"""Service-owned request and response compatibility modules."""

__all__ = [
	"ImageRequest",
	"ImageResponse",
	"LLMRequest",
	"OpenVoiceTTSRequest",
	"Rect",
]


def __getattr__(name: str):
	if name == "ImageRequest":
		from ..art.managers.stablediffusion.image_request import ImageRequest

		return ImageRequest
	if name == "ImageResponse":
		from ..art.managers.stablediffusion.image_response import ImageResponse

		return ImageResponse
	if name == "LLMRequest":
		from .llm_request import LLMRequest

		return LLMRequest
	if name == "OpenVoiceTTSRequest":
		from .tts_request import OpenVoiceTTSRequest

		return OpenVoiceTTSRequest
	if name == "Rect":
		from ..art.managers.stablediffusion.rect import Rect

		return Rect
	raise AttributeError(f"module {__name__} has no attribute {name}")