import unittest
from airunner.workers.tts_generator_worker import TTSGeneratorWorker

class TestTTSGeneratorWorker(unittest.TestCase):

    def test_split_text_at_punctuation(self):
        test_cases = [
            ("Hello world.", ["Hello world"]),
            ("Hello world. How are you?", ["Hello world", "How are you"]),
            ("Hello! How are you? I'm fine.", ["Hello", "How are you", "I'm fine"]),
            ("No punctuation here", ["No punctuation here"]),
            ("Multiple\nlines\nhere", ["Multiple", "lines", "here"]),
            ("Comma, separated, values", ["Comma", "separated", "values"]),
            ("Mixed punctuation! Really? Yes.", ["Mixed punctuation", "Really", "Yes"]),
            ("The time is 12:45.", ["The time is 1245"]),
            ("Meet me at 09:30 AM.", ["Meet me at 0930 AM"]),
            ("It happened at 23:59:59.", ["It happened at 235959"]),
        ]

        for text, expected_chunks in test_cases:
            with self.subTest(text=text, expected_chunks=expected_chunks):
                self.assertEqual(TTSGeneratorWorker._split_text_at_punctuation(text), expected_chunks)

if __name__ == '__main__':
    unittest.main()
