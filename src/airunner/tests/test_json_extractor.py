import unittest
from airunner.aihandler.llm.agent import AIRunnerAgent


class TestJSONExtractor(unittest.TestCase):
    def setUp(self):
        self.agent = AIRunnerAgent()

    def test_extract_json_objects(self):
        test_string = """{
            "prompt": "Create a photo of a blue whale breaching out of the water.",
            "type": "photo"
        }"""
        result = self.agent.extract_json_objects(test_string)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['prompt'], "Create a photo of a blue whale breaching out of the water.")
        self.assertEqual(result[0]['type'], "photo")

    def test_with_json_block(self):
        test_string = '```json\n{ "prompt": "Create a photo of a blue whale breaching out of the water.", "type": "photo" }\n```'
        result = self.agent.extract_json_objects(test_string)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['prompt'], "Create a photo of a blue whale breaching out of the water.")
        self.assertEqual(result[0]['type'], "photo")

    def test_with_json_block_and_text(self):
        test_string = 'Some text here\n\n```json\n{ "prompt": "Create a photo of a blue whale breaching out of the water.", "type": "photo" }\n```\n\nmore text here'
        result = self.agent.extract_json_objects(test_string)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['prompt'], "Create a photo of a blue whale breaching out of the water.")
        self.assertEqual(result[0]['type'], "photo")

    def test_json_block_two(self):
        test_string = """```json
{
   "prompt": "Create a photo of a blue whale breaching out of the water.",
   "type": "photo"
}
```"""
        result = self.agent.extract_json_objects(test_string)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['prompt'], "Create a photo of a blue whale breaching out of the water.")
        self.assertEqual(result[0]['type'], "photo")