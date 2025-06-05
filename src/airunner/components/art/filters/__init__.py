"""Image filters package for AI Runner.

This package contains filter implementations that can be applied to images
in the AI Runner application. Each filter inherits from the BaseFilter class
and implements the apply_filter method.
"""

from airunner.components.art.filters.base_filter import BaseFilter
from airunner.components.art.filters.box_blur import BoxBlur
from airunner.components.art.filters.color_balance import ColorBalanceFilter
from airunner.components.art.filters.dither import Dither
from airunner.components.art.filters.film import FilmFilter
from airunner.components.art.filters.gaussian_blur import GaussianBlur
from airunner.components.art.filters.halftone import HalftoneFilter
from airunner.components.art.filters.invert import Invert
from airunner.components.art.filters.pixel_art import PixelFilter
from airunner.components.art.filters.registration_error import (
    RegistrationErrorFilter,
)
from airunner.components.art.filters.rgb_noise import RGBNoiseFilter
from airunner.components.art.filters.saturation import SaturationFilter
from airunner.components.art.filters.unsharp_mask import UnsharpMask

__all__ = [
    "BaseFilter",
    "BoxBlur",
    "ColorBalanceFilter",
    "Dither",
    "FilmFilter",
    "GaussianBlur",
    "HalftoneFilter",
    "Invert",
    "PixelFilter",
    "RegistrationErrorFilter",
    "RGBNoiseFilter",
    "SaturationFilter",
    "UnsharpMask",
]
