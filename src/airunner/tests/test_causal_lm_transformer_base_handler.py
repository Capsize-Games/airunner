import unittest
from unittest.mock import MagicMock
from airunner.aihandler.llm.casual_lm_transfformer_base_handler import CausalLMTransformerBaseHandler
from airunner.enums import LLMActionType


class TestCausalLMTransformerBaseHandler(unittest.TestCase):
    def setUp(self):
        self.handler = CausalLMTransformerBaseHandler()

    def test_process_data(self):
        # Prepare test data
        data = {
            "username": "test_user",
            "botname": "test_bot",
            "bot_mood": "happy",
            "bot_personality": "friendly",
            "use_personality": True,
            "use_mood": True,
            "use_guardrails": True,
            "use_system_instructions": True,
            "assign_names": True,
            "prompt_template": "test_template",
            "guardrails_prompt": "test_guardrails",
            "system_instructions": "test_instructions",
            "batch_size": 1,
            "vision_history": [],
            "action": LLMActionType.CHAT.value
        }

        # Call the method under test
        self.handler.process_data(data)

        # Assert that the handler's attributes were set correctly
        self.assertEqual(self.handler._username, "test_user")
        self.assertEqual(self.handler._botname, "test_bot")
        self.assertEqual(self.handler.bot_mood, "happy")
        self.assertEqual(self.handler.bot_personality, "friendly")
        self.assertTrue(self.handler.use_personality)
        self.assertTrue(self.handler.use_mood)
        self.assertTrue(self.handler.use_guardrails)
        self.assertTrue(self.handler.use_system_instructions)
        self.assertTrue(self.handler.assign_names)
        self.assertEqual(self.handler.prompt_template, "test_template")
        self.assertEqual(self.handler.guardrails_prompt, "test_guardrails")
        self.assertEqual(self.handler.system_instructions, "test_instructions")
        self.assertEqual(self.handler.batch_size, 1)
        self.assertEqual(self.handler.vision_history, [])
        self.assertEqual(self.handler.action, LLMActionType.CHAT)

    def test_chat_template(self):
        # Test when is_mistral is True
        self.handler.model_path = "mistral"
        expected_template = (
            "{% for message in messages %}"
            "{% if message['role'] == 'system' %}"
            "{{ '[INST] <<SYS>>' + message['content'] + ' <</SYS>>[/INST]' }}"
            "{% elif message['role'] == 'user' %}"
            "{{ '[INST]' + message['content'] + ' [/INST]' }}"
            "{% elif message['role'] == 'assistant' %}"
            "{{ message['content'] + eos_token + ' ' }}"
            "{% endif %}"
            "{% endfor %}"
        )
        self.assertEqual(self.handler.chat_template, expected_template)

        # Test when is_mistral is False
        self.handler.model_path = "asdf"
        self.assertIsNone(self.handler.chat_template)

    def test_username(self):
        # Test when assign_names is True
        self.handler._username = "test_user"
        self.handler.assign_names = True
        self.assertEqual(self.handler.username, "test_user")

        # Test when assign_names is False
        self.handler.assign_names = False
        self.assertEqual(self.handler.username, "User")

    def test_botname(self):
        # Test when assign_names is True
        self.handler._botname = "test_bot"
        self.handler.assign_names = True
        self.assertEqual(self.handler.botname, "test_bot")

        # Test when assign_names is False
        self.handler.assign_names = False
        self.assertEqual(self.handler.botname, "Assistant")

if __name__ == '__main__':
    unittest.main()