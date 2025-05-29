import unittest
from unittest.mock import patch, MagicMock

from airunner.handlers.llm.llm_request import (
    LLMRequest,
    OpenrouterMistralRequest,
)


class TestLLMRequest(unittest.TestCase):
    """Test suite for the LLMRequest class functionality."""

    def test_to_dict_basic(self):
        """Test the basic to_dict conversion functionality."""
        # Create a request with known values
        request = LLMRequest(
            do_sample=True,
            early_stopping=True,
            eta_cutoff=100,
            length_penalty=1.2,
            max_new_tokens=50,
            min_length=5,
            no_repeat_ngram_size=3,
            num_beams=4,
            num_return_sequences=2,
            repetition_penalty=1.5,
            temperature=0.8,
            top_k=40,
            top_p=0.95,
            use_cache=True,
            do_tts_reply=True,
        )

        # Convert to dict
        result = request.to_dict()

        # Verify key properties
        self.assertEqual(result["do_sample"], True)
        self.assertEqual(result["max_new_tokens"], 50)
        self.assertEqual(result["min_length"], 5)
        self.assertEqual(result["num_beams"], 4)
        self.assertEqual(result["num_return_sequences"], 2)
        self.assertEqual(result["use_cache"], True)

        # Verify corrected values
        self.assertGreaterEqual(result["repetition_penalty"], 0.0001)
        self.assertGreaterEqual(result["temperature"], 0.0001)
        self.assertGreaterEqual(result["top_p"], 0.0001)

        # Verify special handling for beam-based params
        self.assertIn("early_stopping", result)
        self.assertIn("length_penalty", result)

    def test_to_dict_single_beam(self):
        """Test that beam-specific parameters are removed when num_beams=1."""
        # Create a request with a single beam
        request = LLMRequest(
            num_beams=1, length_penalty=1.2, early_stopping=True
        )

        # Convert to dict
        result = request.to_dict()

        # Verify beam-specific parameters are removed
        self.assertNotIn("early_stopping", result)
        self.assertNotIn("length_penalty", result)

    def test_from_values(self):
        """Test the from_values factory method with scaling."""
        # Create a request using the factory method
        request = LLMRequest.from_values(
            do_sample=True,
            early_stopping=True,
            eta_cutoff=100,
            length_penalty=1200,  # Will be divided by 1000
            max_new_tokens=50,
            min_length=5,
            no_repeat_ngram_size=3,
            num_beams=4,
            num_return_sequences=2,
            repetition_penalty=150,  # Will be divided by 100
            temperature=8000,  # Will be divided by 10000
            top_k=40,
            top_p=950,  # Will be divided by 1000
            use_cache=True,
        )

        # Verify the scaling was applied correctly
        self.assertAlmostEqual(request.length_penalty, 1.2)
        self.assertAlmostEqual(request.repetition_penalty, 1.5)
        self.assertAlmostEqual(request.temperature, 0.8)
        self.assertAlmostEqual(request.top_p, 0.95)

    @patch("airunner.handlers.llm.llm_request.Chatbot")
    def test_from_chatbot(self, mock_chatbot_class):
        """Test creating a request from a chatbot object."""
        # Set up mock chatbot
        mock_chatbot = MagicMock()
        mock_chatbot.do_sample = True
        mock_chatbot.early_stopping = True
        mock_chatbot.eta_cutoff = 100
        mock_chatbot.length_penalty = 1200
        mock_chatbot.max_new_tokens = 50
        mock_chatbot.min_length = 5
        mock_chatbot.ngram_size = 3
        mock_chatbot.num_beams = 4
        mock_chatbot.num_return_sequences = 2
        mock_chatbot.repetition_penalty = 150
        mock_chatbot.temperature = 8000
        mock_chatbot.top_k = 40
        mock_chatbot.top_p = 950
        mock_chatbot.use_cache = True

        # Mock the objects manager
        mock_objects = MagicMock()
        mock_objects.get.return_value = mock_chatbot
        mock_objects.first.return_value = mock_chatbot
        mock_chatbot_class.objects = mock_objects

        # Create a request from the chatbot
        request = LLMRequest.from_chatbot()

        # Verify the values were transferred and scaled correctly
        self.assertEqual(request.do_sample, mock_chatbot.do_sample)
        self.assertEqual(request.early_stopping, mock_chatbot.early_stopping)
        self.assertEqual(request.eta_cutoff, mock_chatbot.eta_cutoff)
        self.assertAlmostEqual(request.length_penalty, 1.2)
        self.assertEqual(request.max_new_tokens, mock_chatbot.max_new_tokens)
        self.assertEqual(request.min_length, mock_chatbot.min_length)
        self.assertEqual(request.no_repeat_ngram_size, mock_chatbot.ngram_size)
        self.assertEqual(request.num_beams, mock_chatbot.num_beams)
        self.assertEqual(
            request.num_return_sequences, mock_chatbot.num_return_sequences
        )
        self.assertAlmostEqual(request.repetition_penalty, 1.5)
        self.assertAlmostEqual(request.temperature, 0.8)
        self.assertEqual(
            request.top_k, mock_chatbot.top_k
        )  # Fixed: This should match the mock value
        self.assertAlmostEqual(request.top_p, 0.95)
        self.assertEqual(request.use_cache, mock_chatbot.use_cache)

    def test_openrouter_mistral_request(self):
        """Test the OpenrouterMistralRequest specialized class."""
        # Create an OpenRouter request
        request = OpenrouterMistralRequest(
            max_tokens=100,
            temperature=0.5,
            seed=42,
            top_p=0.9,
            top_k=50,
            frequency_penalty=0.2,
            presence_penalty=0.1,
            repetition_penalty=0.3,
        )

        # Convert to dict
        result = request.to_dict()

        # Verify OpenRouter-specific parameters
        self.assertEqual(result["max_tokens"], 100)
        self.assertEqual(result["seed"], 42)
        self.assertAlmostEqual(result["frequency_penalty"], 0.2)
        self.assertAlmostEqual(result["presence_penalty"], 0.1)
        self.assertAlmostEqual(result["repetition_penalty"], 0.3)

    @patch("airunner.handlers.llm.llm_request.LLMGeneratorSettings")
    @patch("airunner.handlers.llm.llm_request.Chatbot")
    def test_from_llm_settings_override(
        self, mock_chatbot_class, mock_settings_class
    ):
        """Test from_llm_settings with override_parameters True and False."""
        # Setup for override_parameters True
        mock_settings = MagicMock()
        mock_settings.override_parameters = True
        mock_settings.do_sample = True
        mock_settings.early_stopping = False
        mock_settings.eta_cutoff = 123
        mock_settings.length_penalty = 456
        mock_settings.max_new_tokens = 789
        mock_settings.min_length = 10
        mock_settings.ngram_size = 2
        mock_settings.num_beams = 3
        mock_settings.sequences = 4
        mock_settings.repetition_penalty = 500
        mock_settings.temperature = 10000
        mock_settings.top_k = 7
        mock_settings.top_p = 900
        mock_settings.use_cache = False

        mock_settings_class.objects.get.return_value = mock_settings
        mock_settings_class.objects.first.return_value = mock_settings

        # Should use override_parameters path
        req = LLMRequest.from_llm_settings()
        self.assertTrue(req.do_sample)
        self.assertFalse(req.early_stopping)
        self.assertEqual(req.eta_cutoff, 123)
        self.assertAlmostEqual(req.length_penalty, 0.456)
        self.assertEqual(req.max_new_tokens, 789)
        self.assertEqual(req.min_length, 10)
        self.assertEqual(req.no_repeat_ngram_size, 2)
        self.assertEqual(req.num_beams, 3)
        self.assertEqual(req.num_return_sequences, 4)
        self.assertAlmostEqual(req.repetition_penalty, 5.0)
        self.assertAlmostEqual(req.temperature, 1.0)
        self.assertEqual(req.top_k, 7)
        self.assertAlmostEqual(req.top_p, 0.9)
        self.assertFalse(req.use_cache)

        # Setup for override_parameters False (should fallback to from_chatbot)
        mock_settings.override_parameters = False
        # mock_settings.current_chatbot = 42  # Removed: no longer used
        mock_cb = MagicMock()
        mock_chatbot_class.objects.get.return_value = mock_cb
        mock_cb.do_sample = False
        mock_cb.early_stopping = True
        mock_cb.eta_cutoff = 1
        mock_cb.length_penalty = 1000
        mock_cb.max_new_tokens = 2
        mock_cb.min_length = 3
        mock_cb.ngram_size = 4
        mock_cb.num_beams = 5
        mock_cb.num_return_sequences = 6
        mock_cb.repetition_penalty = 700
        mock_cb.temperature = 20000
        mock_cb.top_k = 8
        mock_cb.top_p = 1000
        mock_cb.use_cache = True
        req2 = LLMRequest.from_llm_settings()
        self.assertFalse(req2.do_sample)
        self.assertTrue(req2.early_stopping)
        self.assertEqual(req2.eta_cutoff, 1)
        self.assertAlmostEqual(req2.length_penalty, 1.0)
        self.assertEqual(req2.max_new_tokens, 2)
        self.assertEqual(req2.min_length, 3)
        self.assertEqual(req2.no_repeat_ngram_size, 4)
        self.assertEqual(req2.num_beams, 5)
        self.assertEqual(req2.num_return_sequences, 6)
        self.assertAlmostEqual(req2.repetition_penalty, 7.0)
        self.assertAlmostEqual(req2.temperature, 2.0)
        self.assertEqual(req2.top_k, 8)
        self.assertAlmostEqual(req2.top_p, 1.0)
        self.assertTrue(req2.use_cache)

    @patch("airunner.handlers.llm.llm_request.LLMGeneratorSettings")
    @patch("airunner.handlers.llm.llm_request.Chatbot")
    def test_from_default(self, mock_chatbot_class, mock_settings_class):
        """Test from_default delegates to from_llm_settings and returns expected values."""
        mock_settings = MagicMock()
        mock_settings.override_parameters = True
        mock_settings.do_sample = True
        mock_settings.early_stopping = True
        mock_settings.eta_cutoff = 1
        mock_settings.length_penalty = 1000
        mock_settings.max_new_tokens = 2
        mock_settings.min_length = 3
        mock_settings.ngram_size = 4
        mock_settings.num_beams = 5
        mock_settings.sequences = 6
        mock_settings.repetition_penalty = 700
        mock_settings.temperature = 20000
        mock_settings.top_k = 8
        mock_settings.top_p = 1000
        mock_settings.use_cache = True
        mock_settings_class.objects.first.return_value = mock_settings
        req = LLMRequest.from_default()
        self.assertTrue(req.do_sample)
        self.assertTrue(req.early_stopping)
        self.assertEqual(req.eta_cutoff, 1)
        self.assertAlmostEqual(req.length_penalty, 1.0)
        self.assertEqual(req.max_new_tokens, 2)
        self.assertEqual(req.min_length, 3)
        self.assertEqual(req.no_repeat_ngram_size, 4)
        self.assertEqual(req.num_beams, 5)
        self.assertEqual(req.num_return_sequences, 6)
        self.assertAlmostEqual(req.repetition_penalty, 7.0)
        self.assertAlmostEqual(req.temperature, 2.0)
        self.assertEqual(req.top_k, 8)
        self.assertAlmostEqual(req.top_p, 1.0)
        self.assertTrue(req.use_cache)

    def test_to_dict_min_value_clamping_and_removal(self):
        """Test to_dict clamps min values and removes node_id/use_memory. Also checks key removal logic."""
        # Case 1: num_beams=1, keys should be removed
        req = LLMRequest(
            length_penalty=0.0,
            repetition_penalty=0.0,
            temperature=0.0,
            top_p=0.0,
            node_id="test",
            use_memory=False,
            num_beams=1,
            early_stopping=True,
        )
        d = req.to_dict()
        self.assertNotIn("length_penalty", d)
        self.assertNotIn("early_stopping", d)
        self.assertGreaterEqual(d["repetition_penalty"], 0.0001)
        self.assertGreaterEqual(d["temperature"], 0.0001)
        self.assertGreaterEqual(d["top_p"], 0.0001)
        self.assertNotIn("node_id", d)
        self.assertNotIn("use_memory", d)

        # Case 2: num_beams>1, keys should be present and clamped
        req2 = LLMRequest(
            length_penalty=0.0,
            repetition_penalty=0.0,
            temperature=0.0,
            top_p=0.0,
            num_beams=2,
            early_stopping=True,
        )
        d2 = req2.to_dict()
        self.assertIn("length_penalty", d2)
        self.assertIn("early_stopping", d2)
        self.assertGreaterEqual(d2["length_penalty"], 0.0001)
        self.assertGreaterEqual(d2["repetition_penalty"], 0.0001)
        self.assertGreaterEqual(d2["temperature"], 0.0001)
        self.assertGreaterEqual(d2["top_p"], 0.0001)

    def test_openrouter_mistral_request_min_value_clamping(self):
        """Test OpenrouterMistralRequest clamps min values in to_dict."""
        req = OpenrouterMistralRequest(
            frequency_penalty=0.0,
            presence_penalty=0.0,
            repetition_penalty=0.0,
            temperature=0.0,
            top_p=0.0,
        )
        d = req.to_dict()
        self.assertGreaterEqual(d["frequency_penalty"], 0.0001)
        self.assertGreaterEqual(d["presence_penalty"], 0.0001)
        self.assertGreaterEqual(d["repetition_penalty"], 0.0001)
        self.assertGreaterEqual(d["temperature"], 0.0001)
        self.assertGreaterEqual(d["top_p"], 0.0001)


if __name__ == "__main__":
    unittest.main()
