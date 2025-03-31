"""Tests for the image filters package.

This module contains unit tests for the filters in the airunner.filters package.
"""

import unittest
from unittest.mock import MagicMock, patch
import numpy as np
from PIL import Image

from airunner.filters import (
    BaseFilter,
    BoxBlur,
    ColorBalanceFilter,
    Dither,
    FilmFilter,
    GaussianBlur,
    HalftoneFilter,
    Invert,
    PixelFilter,
    RegistrationErrorFilter,
    RGBNoiseFilter,
    SaturationFilter,
    UnsharpMask
)


class TestBaseFilter(unittest.TestCase):
    """Test the BaseFilter class functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_image = Image.new('RGB', (100, 100), color='white')
    
    def test_init(self):
        """Test filter initialization with kwargs."""
        test_filter = BaseFilter(param1='value1', param2='value2')
        self.assertEqual(test_filter.param1, 'value1')
        self.assertEqual(test_filter.param2, 'value2')
    
    def test_filter_caching(self):
        """Test image caching behavior."""
        # Create a test subclass
        class TestFilter(BaseFilter):
            def apply_filter(self, image, do_reset=False):
                self.apply_filter_called = True
                self.do_reset_passed = do_reset
                return image
        
        test_filter = TestFilter()
        test_filter.apply_filter_called = False
        test_filter.do_reset_passed = None
        
        # First call should set do_reset to True
        test_filter.filter(self.test_image)
        self.assertTrue(test_filter.apply_filter_called)
        self.assertTrue(test_filter.do_reset_passed)
        
        # Reset for next test
        test_filter.apply_filter_called = False
        test_filter.do_reset_passed = None
        
        # Second call with same image should set do_reset to False
        test_filter.filter(self.test_image)
        self.assertTrue(test_filter.apply_filter_called)
        self.assertFalse(test_filter.do_reset_passed)
        
        # Reset for next test
        test_filter.apply_filter_called = False
        test_filter.do_reset_passed = None
        
        # Different image should set do_reset to True again
        new_image = Image.new('RGB', (100, 100), color='black')
        test_filter.filter(new_image)
        self.assertTrue(test_filter.apply_filter_called)
        self.assertTrue(test_filter.do_reset_passed)


class TestBoxBlur(unittest.TestCase):
    """Test the BoxBlur filter."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_image = Image.new('RGB', (100, 100), color='white')
    
    def test_apply_filter(self):
        """Test the box blur filter application."""
        filter_instance = BoxBlur(radius=2)
        result = filter_instance.filter(self.test_image)
        
        # The result should be an image
        self.assertIsInstance(result, Image.Image)
        
        # The dimensions should remain the same
        self.assertEqual(result.size, self.test_image.size)


class TestInvert(unittest.TestCase):
    """Test the Invert filter."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_image = Image.new('RGB', (100, 100), color='white')
    
    def test_apply_filter(self):
        """Test the invert filter application."""
        filter_instance = Invert()
        result = filter_instance.filter(self.test_image)
        
        # The result should be an image
        self.assertIsInstance(result, Image.Image)
        
        # For a white image, inversion should result in a black image
        # Get the pixel at (0,0)
        pixel = result.getpixel((0, 0))
        # All RGB values should be 0 (black)
        self.assertEqual(pixel[0], 0)
        self.assertEqual(pixel[1], 0)
        self.assertEqual(pixel[2], 0)


class TestRGBNoiseFilter(unittest.TestCase):
    """Test the RGBNoiseFilter."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_image = Image.new('RGBA', (100, 100), color='white')
    
    @patch('numpy.random.uniform')
    def test_apply_filter(self, mock_uniform):
        """Test the RGB noise filter application."""
        # Mock the random function to return a predictable value
        mock_uniform.return_value = np.ones((100, 100))
        
        # Create filter with specific noise values
        filter_instance = RGBNoiseFilter(red=10, green=20, blue=30)
        result = filter_instance.filter(self.test_image)
        
        # The result should be an image
        self.assertIsInstance(result, Image.Image)
        
        # Check that numpy.random.uniform was called correctly
        mock_uniform.assert_called()


class TestDither(unittest.TestCase):
    """Test the Dither filter."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_image = Image.new('RGB', (100, 100), color='white')
    
    def test_apply_filter(self):
        """Test the dither filter application."""
        filter_instance = Dither(threshold=0.5)
        result = filter_instance.filter(self.test_image)
        
        # The result should be an image
        self.assertIsInstance(result, Image.Image)
        
        # Mode should be '1' (binary image)
        self.assertEqual(result.mode, '1')


if __name__ == '__main__':
    unittest.main()