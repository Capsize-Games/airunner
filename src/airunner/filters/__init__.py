"""Image filters package for AI Runner.

This package contains filter implementations that can be applied to images
in the AI Runner application. Each filter inherits from the BaseFilter class
and implements the apply_filter method.
"""

from airunner.filters.base_filter import BaseFilter
from airunner.filters.box_blur import BoxBlur
from airunner.filters.color_balance import ColorBalanceFilter
from airunner.filters.dither import Dither
from airunner.filters.film import FilmFilter
from airunner.filters.gaussian_blur import GaussianBlur
from airunner.filters.halftone import HalftoneFilter
from airunner.filters.invert import Invert
from airunner.filters.pixel_art import PixelFilter
from airunner.filters.registration_error import RegistrationErrorFilter
from airunner.filters.rgb_noise import RGBNoiseFilter
from airunner.filters.saturation import SaturationFilter
from airunner.filters.unsharp_mask import UnsharpMask

__all__ = [
    'BaseFilter',
    'BoxBlur',
    'ColorBalanceFilter',
    'Dither',
    'FilmFilter', 
    'GaussianBlur',
    'HalftoneFilter',
    'Invert',
    'PixelFilter',
    'RegistrationErrorFilter',
    'RGBNoiseFilter',
    'SaturationFilter',
    'UnsharpMask',
]