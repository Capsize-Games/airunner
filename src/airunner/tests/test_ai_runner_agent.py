import unittest
from unittest.mock import MagicMock
from airunner.aihandler.llm.agent import AIRunnerAgent
from airunner.enums import LLMChatRole


class TestAIRunnerAgent(unittest.TestCase):
    def setUp(self):
        self.agent = AIRunnerAgent()

    def test_interrupt_process(self):
        self.agent.interrupt_process()
        self.assertTrue(self.agent.do_interrupt)

    def test_do_interrupt_process(self):
        self.agent.do_interrupt = True
        interrupt = self.agent.do_interrupt_process()
        self.assertTrue(interrupt)
        self.assertFalse(self.agent.do_interrupt)

    def test_use_cuda(self):
        torch_cuda = MagicMock()
        torch_cuda.is_available.return_value = True
        self.agent.torch = torch_cuda
        self.assertTrue(self.agent.use_cuda)

    def test_cuda_index(self):
        self.assertEqual(self.agent.cuda_index, 0)

    def test_extract_json_objects(self):
        json_string = '{"key": "value"}'
        expected_result = [{"key": "value"}]
        actual_result = self.agent.extract_json_objects(json_string)
        self.assertEqual(actual_result, expected_result)

    def test_extract_json_objects_with_invalid_json(self):
        invalid_json_string = '{"key": "value",}'
        expected_result = []
        actual_result = self.agent.extract_json_objects(invalid_json_string)
        self.assertEqual(actual_result, expected_result)

    def test_add_message_to_history(self):
        message = "Test message"
        role = LLMChatRole.ASSISTANT
        self.agent.add_message_to_history(message, role)
        self.assertEqual(self.agent.history[-1], {'content': message, 'role': role.value})


if __name__ == '__main__':
    unittest.main()
