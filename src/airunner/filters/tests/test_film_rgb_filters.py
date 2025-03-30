import unittest
import numpy as np
from PIL import Image

from airunner.filters.rgb_noise import RGBNoiseFilter
from airunner.filters.film import FilmFilter


class TestImageFilters(unittest.TestCase):
    def setUp(self):
        # Create a simple test image
        self.test_image = Image.new('RGBA', (100, 100), (255, 255, 255, 255))

    def test_rgb_noise_filter(self):
        # Create filter with noise values
        filter_instance = RGBNoiseFilter(red=10.0, green=5.0, blue=15.0)
        
        # Apply filter to test image
        result_image = filter_instance.filter(self.test_image)
        
        # Check that result is still an image
        self.assertIsInstance(result_image, Image.Image)
        
        # Check dimensions are preserved
        self.assertEqual(result_image.size, self.test_image.size)
        
        # Check mode is preserved (RGBA)
        self.assertEqual(result_image.mode, "RGBA")
        
        # Convert to numpy arrays to compare pixel values
        original_array = np.array(self.test_image)
        result_array = np.array(result_image)
        
        # Ensure the arrays are different (noise was applied)
        self.assertFalse(np.array_equal(original_array, result_array))

    def test_film_filter(self):
        # Create filter with blur radius and noise values
        filter_instance = FilmFilter(radius=2.0, red=5.0, green=5.0, blue=5.0)
        
        # Apply filter to test image
        result_image = filter_instance.filter(self.test_image)
        
        # Check that result is still an image
        self.assertIsInstance(result_image, Image.Image)
        
        # Check dimensions are preserved
        self.assertEqual(result_image.size, self.test_image.size)
        
        # Check mode is preserved (RGBA)
        self.assertEqual(result_image.mode, "RGBA")
        
        # Convert to numpy arrays to compare pixel values
        original_array = np.array(self.test_image)
        result_array = np.array(result_image)
        
        # Ensure the arrays are different (blur and noise were applied)
        self.assertFalse(np.array_equal(original_array, result_array))


if __name__ == '__main__':
    unittest.main()