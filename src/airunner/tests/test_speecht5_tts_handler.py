import unittest
from airunner.handlers.tts.speecht5_tts_handler import SpeechT5TTSHandler

class TestSpeechT5TTSHandler(unittest.TestCase):

    def test_replace_numbers_with_words(self):
        handler = SpeechT5TTSHandler()

        # Test cases
        test_cases = {
            "12:00PM": "twelve P M",
            "3:34AM": "three thirty four A M",
            "12:33pm": "twelve thirty three P M",
            "34PM": "thirty four P M",
            "I have 2 apples": "I have two apples",
            "The time is 12:30": "The time is twelve thirty",
            "He is 25 years old": "He is twenty five years old",
            "Room number 404": "Room number four hundred and four",
            "No numbers here": "No numbers here"
        }

        for input_text, expected_output in test_cases.items():
            with self.subTest(input_text=input_text, expected_output=expected_output):
                self.assertEqual(handler._replace_numbers_with_words(input_text), expected_output)

    def test_roman_to_int(self):
        handler = SpeechT5TTSHandler()

        # Test cases for Roman numerals
        test_cases = {
            "I": "1",
            "IV": "4",
            "IX": "9",
            "XII": "12",
            "XXI": "21",
            "XL": "40",
            "L": "50",
            "XC": "90",
            "C": "100",
            "CD": "400",
            "D": "500",
            "CM": "900",
            "M": "1000",
            "MMXXI": "2021",
            "This is a IV test": "This is a 4 test",
            "A test with no roman numerals": "A test with no roman numerals",
        }

        for roman, expected in test_cases.items():
            with self.subTest(roman=roman, expected=expected):
                self.assertEqual(handler._roman_to_int(roman), expected)

    def test_replace_unspeakable_characters(self):
        handler = SpeechT5TTSHandler()

        # Test cases
        test_cases = {
            "Hello... world!": "Hello  world!",
            "This is an ellipsis…": "This is an ellipsis ",
            "Smart quotes ‘single’ and “double”": "Smart quotes single and double",
            "Em dash — and en dash –": "Em dash  and en dash ",
            "Tabs\tand\nnewlines\r\n": "Tabs and newlines ",
        }

        for input_text, expected_output in test_cases.items():
            with self.subTest(input_text=input_text, expected_output=expected_output):
                self.assertEqual(handler._replace_unspeakable_characters(input_text), expected_output)

    def test_strip_emoji_characters(self):
        handler = SpeechT5TTSHandler()

        # Test cases
        test_cases = {
            "😊": "",
            "😂": "",
            "👍": "",
            "🏆": "",
            "😊😂👍🏆": "",
            "😊😊😊": "",
            "😂👍🏆😊": "",
            "🏆👍😂😊": "",
            "👍🏆😊😂": "",
            "No emojis here": "No emojis here"
        }

        for input_text, expected_output in test_cases.items():
            with self.subTest(input_text=input_text, expected_output=expected_output):
                self.assertEqual(handler._strip_emoji_characters(input_text), expected_output)

    def test_prepare_text(self):
        handler = SpeechT5TTSHandler()

        # Test cases
        test_cases = {
            "Emoji 😊 should be removed": "Emoji should be removed",
            "Mixed 😊 text  with ‘quotes’ and — dashes": "Mixed text with quotes and dashes",
            "😊": "",
            "Hello 😊": "Hello ",
            "😊😊😊": "",
            "Mixed text 😊 with emoji": "Mixed text with emoji",
            "Multiple emojis 😊😂👍": "Multiple emojis ",
            "Text with various emojis 😊😂👍🏆": "Text with various emojis ",
            "Emojis at the end 😊😂👍🏆": "Emojis at the end ",
            "No emojis here": "No emojis here"
        }

        for input_text, expected_output in test_cases.items():
            with self.subTest(input_text=input_text, expected_output=expected_output):
                self.assertEqual(handler._prepare_text(input_text), expected_output)

if __name__ == '__main__':
    unittest.main()
