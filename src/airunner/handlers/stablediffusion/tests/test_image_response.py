import unittest
from PIL import Image
from src.airunner.handlers.stablediffusion.image_response import ImageResponse
from src.airunner.handlers.stablediffusion.rect import Rect

class TestImageResponse(unittest.TestCase):
    def test_to_dict(self):
        rect = Rect(x=10, y=20, width=30, height=40)
        response = ImageResponse(
            images=None,
            data={"key": "value"},
            nsfw_content_detected=False,
            active_rect=rect,
            is_outpaint=True
        )
        expected_dict = {
            "images": None,
            "data": {"key": "value"},
            "nsfw_content_detected": False,
            "active_rect": {
                "x": 10,
                "y": 20,
                "width": 30,
                "height": 40,
            },
            "is_outpaint": True,
        }
        self.assertEqual(response.to_dict(), expected_dict)

if __name__ == "__main__":
    unittest.main()