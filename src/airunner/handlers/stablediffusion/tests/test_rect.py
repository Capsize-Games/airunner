import unittest
from src.airunner.handlers.stablediffusion.rect import Rect

class TestRect(unittest.TestCase):
    def test_left(self):
        rect = Rect(x=10, y=20, width=30, height=40)
        self.assertEqual(rect.left(), 10)

    def test_top(self):
        rect = Rect(x=10, y=20, width=30, height=40)
        self.assertEqual(rect.top(), 20)

    def test_translate(self):
        rect = Rect(x=10, y=20, width=30, height=40)
        rect.translate(5, -5)
        self.assertEqual(rect.x, 15)
        self.assertEqual(rect.y, 15)

if __name__ == "__main__":
    unittest.main()