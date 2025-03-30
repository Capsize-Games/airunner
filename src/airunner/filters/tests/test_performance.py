import time
import unittest
import numpy as np
from PIL import Image

from airunner.filters.rgb_noise import RGBNoiseFilter
from airunner.filters.film import FilmFilter


class PerformanceTest(unittest.TestCase):
    def setUp(self):
        # Create a larger test image for performance testing
        self.test_image = Image.new('RGBA', (1920, 1080), (255, 255, 255, 255))
    
    def test_rgb_noise_performance(self):
        """Test the performance of the RGB noise filter on a large image"""
        filter_instance = RGBNoiseFilter(red=10.0, green=5.0, blue=15.0)
        
        # Measure execution time
        start_time = time.time()
        result_image = filter_instance.filter(self.test_image)
        end_time = time.time()
        
        execution_time = end_time - start_time
        print(f"\nRGB Noise Filter - Execution time: {execution_time:.4f} seconds for a {self.test_image.size} image")
        
        # Basic validation
        self.assertIsInstance(result_image, Image.Image)
        self.assertEqual(result_image.size, self.test_image.size)
    
    def test_film_filter_performance(self):
        """Test the performance of the Film filter on a large image"""
        filter_instance = FilmFilter(radius=2.0, red=5.0, green=5.0, blue=5.0)
        
        # Measure execution time
        start_time = time.time()
        result_image = filter_instance.filter(self.test_image)
        end_time = time.time()
        
        execution_time = end_time - start_time
        print(f"Film Filter - Execution time: {execution_time:.4f} seconds for a {self.test_image.size} image")
        
        # Basic validation
        self.assertIsInstance(result_image, Image.Image)
        self.assertEqual(result_image.size, self.test_image.size)


if __name__ == '__main__':
    unittest.main()