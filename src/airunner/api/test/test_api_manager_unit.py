"""
Unit tests for APIManager.
Tests initialization, service creation, and signal emission handling.
"""

import pytest
from unittest.mock import MagicMock, patch, call
from airunner.api.api_manager import APIManager


class TestAPIManager:
    """Test cases for APIManager"""

    @pytest.fixture
    def mock_emit_signal(self):
        """Mock emit_signal function"""
        return MagicMock()

    def test_init_with_valid_emit_signal(self, mock_emit_signal):
        """Test APIManager initialization with valid emit_signal"""
        with patch("airunner.api.api_manager.LLMAPIService") as mock_llm, patch(
            "airunner.api.api_manager.ARTAPIService"
        ) as mock_art, patch(
            "airunner.api.api_manager.TTSAPIService"
        ) as mock_tts, patch(
            "airunner.api.api_manager.STTAPIService"
        ) as mock_stt, patch(
            "airunner.api.api_manager.VideoAPIService"
        ) as mock_video, patch(
            "airunner.api.api_manager.NodegraphAPIService"
        ) as mock_nodegraph, patch(
            "airunner.api.api_manager.ImageFilterAPIServices"
        ) as mock_image_filter, patch(
            "airunner.api.api_manager.EmbeddingAPIServices"
        ) as mock_embedding, patch(
            "airunner.api.api_manager.LoraAPIServices"
        ) as mock_lora, patch(
            "airunner.api.api_manager.CanvasAPIService"
        ) as mock_canvas, patch(
            "airunner.api.api_manager.ChatbotAPIService"
        ) as mock_chatbot, patch(
            "airunner.api.api_manager.SoundDeviceManager"
        ) as mock_sound_manager:

            api_manager = APIManager(emit_signal=mock_emit_signal)

            # Verify emit_signal is stored correctly
            assert api_manager._emit_signal is mock_emit_signal
            assert api_manager.emit_signal is mock_emit_signal

            # Verify all services are created with correct emit_signal
            mock_llm.assert_called_once_with(emit_signal=mock_emit_signal)
            mock_art.assert_called_once_with(emit_signal=mock_emit_signal)
            mock_tts.assert_called_once_with(emit_signal=mock_emit_signal)
            mock_stt.assert_called_once_with(emit_signal=mock_emit_signal)
            mock_video.assert_called_once_with(emit_signal=mock_emit_signal)
            mock_nodegraph.assert_called_once_with(emit_signal=mock_emit_signal)
            mock_image_filter.assert_called_once_with(emit_signal=mock_emit_signal)
            mock_embedding.assert_called_once_with(emit_signal=mock_emit_signal)
            mock_lora.assert_called_once_with(emit_signal=mock_emit_signal)
            mock_canvas.assert_called_once_with(emit_signal=mock_emit_signal)
            mock_chatbot.assert_called_once_with(emit_signal=mock_emit_signal)
            mock_sound_manager.assert_called_once_with()

            # Verify service instances are assigned
            assert api_manager.llm == mock_llm.return_value
            assert api_manager.art == mock_art.return_value
            assert api_manager.tts == mock_tts.return_value
            assert api_manager.stt == mock_stt.return_value
            assert api_manager.video == mock_video.return_value
            assert api_manager.nodegraph == mock_nodegraph.return_value
            assert api_manager.image_filter == mock_image_filter.return_value
            assert api_manager.embedding == mock_embedding.return_value
            assert api_manager.lora == mock_lora.return_value
            assert api_manager.canvas == mock_canvas.return_value
            assert api_manager.chatbot == mock_chatbot.return_value
            assert api_manager.sounddevice_manager == mock_sound_manager.return_value

    def test_init_with_none_emit_signal(self):
        """Test APIManager initialization with None emit_signal (fallback behavior)"""
        with patch("airunner.api.api_manager.LLMAPIService") as mock_llm, patch(
            "airunner.api.api_manager.ARTAPIService"
        ) as mock_art, patch(
            "airunner.api.api_manager.TTSAPIService"
        ) as mock_tts, patch(
            "airunner.api.api_manager.STTAPIService"
        ) as mock_stt, patch(
            "airunner.api.api_manager.VideoAPIService"
        ) as mock_video, patch(
            "airunner.api.api_manager.NodegraphAPIService"
        ) as mock_nodegraph, patch(
            "airunner.api.api_manager.ImageFilterAPIServices"
        ) as mock_image_filter, patch(
            "airunner.api.api_manager.EmbeddingAPIServices"
        ) as mock_embedding, patch(
            "airunner.api.api_manager.LoraAPIServices"
        ) as mock_lora, patch(
            "airunner.api.api_manager.CanvasAPIService"
        ) as mock_canvas, patch(
            "airunner.api.api_manager.ChatbotAPIService"
        ) as mock_chatbot, patch(
            "airunner.api.api_manager.SoundDeviceManager"
        ) as mock_sound_manager:

            api_manager = APIManager(emit_signal=None)

            # Verify fallback emit_signal is created (should be the no-op function)
            assert api_manager._emit_signal is not None
            assert callable(api_manager._emit_signal)

            # Test that the fallback function is indeed a no-op
            # (should not raise any exceptions when called)
            api_manager._emit_signal("test", data={"test": "value"})

            # Verify all services are created with the fallback emit_signal
            mock_llm.assert_called_once_with(emit_signal=api_manager._emit_signal)
            mock_art.assert_called_once_with(emit_signal=api_manager._emit_signal)
            mock_tts.assert_called_once_with(emit_signal=api_manager._emit_signal)
            mock_stt.assert_called_once_with(emit_signal=api_manager._emit_signal)
            mock_video.assert_called_once_with(emit_signal=api_manager._emit_signal)
            mock_nodegraph.assert_called_once_with(emit_signal=api_manager._emit_signal)
            mock_image_filter.assert_called_once_with(
                emit_signal=api_manager._emit_signal
            )
            mock_embedding.assert_called_once_with(emit_signal=api_manager._emit_signal)
            mock_lora.assert_called_once_with(emit_signal=api_manager._emit_signal)
            mock_canvas.assert_called_once_with(emit_signal=api_manager._emit_signal)
            mock_chatbot.assert_called_once_with(emit_signal=api_manager._emit_signal)
            mock_sound_manager.assert_called_once_with()

    def test_emit_signal_property(self, mock_emit_signal):
        """Test emit_signal property returns correct function"""
        with patch("airunner.api.api_manager.LLMAPIService"), patch(
            "airunner.api.api_manager.ARTAPIService"
        ), patch("airunner.api.api_manager.TTSAPIService"), patch(
            "airunner.api.api_manager.STTAPIService"
        ), patch(
            "airunner.api.api_manager.VideoAPIService"
        ), patch(
            "airunner.api.api_manager.NodegraphAPIService"
        ), patch(
            "airunner.api.api_manager.ImageFilterAPIServices"
        ), patch(
            "airunner.api.api_manager.EmbeddingAPIServices"
        ), patch(
            "airunner.api.api_manager.LoraAPIServices"
        ), patch(
            "airunner.api.api_manager.CanvasAPIService"
        ), patch(
            "airunner.api.api_manager.ChatbotAPIService"
        ), patch(
            "airunner.api.api_manager.SoundDeviceManager"
        ):

            api_manager = APIManager(emit_signal=mock_emit_signal)

            # Test property getter
            assert api_manager.emit_signal is mock_emit_signal
            assert api_manager.emit_signal is api_manager._emit_signal

    def test_service_initialization_order(self, mock_emit_signal):
        """Test that services are initialized in expected order"""
        service_calls = []

        def track_service_init(service_name):
            def mock_service(*args, **kwargs):
                service_calls.append(service_name)
                return MagicMock()

            return mock_service

        with patch(
            "airunner.api.api_manager.LLMAPIService",
            side_effect=track_service_init("llm"),
        ), patch(
            "airunner.api.api_manager.ARTAPIService",
            side_effect=track_service_init("art"),
        ), patch(
            "airunner.api.api_manager.TTSAPIService",
            side_effect=track_service_init("tts"),
        ), patch(
            "airunner.api.api_manager.STTAPIService",
            side_effect=track_service_init("stt"),
        ), patch(
            "airunner.api.api_manager.VideoAPIService",
            side_effect=track_service_init("video"),
        ), patch(
            "airunner.api.api_manager.NodegraphAPIService",
            side_effect=track_service_init("nodegraph"),
        ), patch(
            "airunner.api.api_manager.ImageFilterAPIServices",
            side_effect=track_service_init("image_filter"),
        ), patch(
            "airunner.api.api_manager.EmbeddingAPIServices",
            side_effect=track_service_init("embedding"),
        ), patch(
            "airunner.api.api_manager.LoraAPIServices",
            side_effect=track_service_init("lora"),
        ), patch(
            "airunner.api.api_manager.CanvasAPIService",
            side_effect=track_service_init("canvas"),
        ), patch(
            "airunner.api.api_manager.ChatbotAPIService",
            side_effect=track_service_init("chatbot"),
        ), patch(
            "airunner.api.api_manager.SoundDeviceManager"
        ):

            APIManager(emit_signal=mock_emit_signal)

            # Verify initialization order matches the code structure
            expected_order = [
                "llm",
                "art",
                "image_filter",
                "embedding",
                "lora",
                "canvas",
                "chatbot",
                "tts",
                "stt",
                "video",
                "nodegraph",
            ]
            assert service_calls == expected_order

    def test_fallback_emit_signal_is_callable(self):
        """Test that the fallback emit_signal created when None is passed is callable and safe"""
        with patch("airunner.api.api_manager.LLMAPIService"), patch(
            "airunner.api.api_manager.ARTAPIService"
        ), patch("airunner.api.api_manager.TTSAPIService"), patch(
            "airunner.api.api_manager.STTAPIService"
        ), patch(
            "airunner.api.api_manager.VideoAPIService"
        ), patch(
            "airunner.api.api_manager.NodegraphAPIService"
        ), patch(
            "airunner.api.api_manager.ImageFilterAPIServices"
        ), patch(
            "airunner.api.api_manager.EmbeddingAPIServices"
        ), patch(
            "airunner.api.api_manager.LoraAPIServices"
        ), patch(
            "airunner.api.api_manager.CanvasAPIService"
        ), patch(
            "airunner.api.api_manager.ChatbotAPIService"
        ), patch(
            "airunner.api.api_manager.SoundDeviceManager"
        ):

            api_manager = APIManager(emit_signal=None)

            # Test that fallback function can be called with various arguments without error
            fallback_fn = api_manager._emit_signal

            # These should all work without raising exceptions
            fallback_fn()
            fallback_fn("signal_code")
            fallback_fn("signal_code", {"data": "value"})
            fallback_fn("signal_code", data={"key": "value"})
            fallback_fn(signal="test", data=None, extra_param=123)

    def test_service_attribute_access(self, mock_emit_signal):
        """Test that all service attributes are accessible after initialization"""
        with patch("airunner.api.api_manager.LLMAPIService") as mock_llm, patch(
            "airunner.api.api_manager.ARTAPIService"
        ) as mock_art, patch(
            "airunner.api.api_manager.TTSAPIService"
        ) as mock_tts, patch(
            "airunner.api.api_manager.STTAPIService"
        ) as mock_stt, patch(
            "airunner.api.api_manager.VideoAPIService"
        ) as mock_video, patch(
            "airunner.api.api_manager.NodegraphAPIService"
        ) as mock_nodegraph, patch(
            "airunner.api.api_manager.ImageFilterAPIServices"
        ) as mock_image_filter, patch(
            "airunner.api.api_manager.EmbeddingAPIServices"
        ) as mock_embedding, patch(
            "airunner.api.api_manager.LoraAPIServices"
        ) as mock_lora, patch(
            "airunner.api.api_manager.CanvasAPIService"
        ) as mock_canvas, patch(
            "airunner.api.api_manager.ChatbotAPIService"
        ) as mock_chatbot, patch(
            "airunner.api.api_manager.SoundDeviceManager"
        ) as mock_sound_manager:

            api_manager = APIManager(emit_signal=mock_emit_signal)

            # Test that all expected attributes exist and return correct instances
            services = [
                ("llm", mock_llm),
                ("art", mock_art),
                ("tts", mock_tts),
                ("stt", mock_stt),
                ("video", mock_video),
                ("nodegraph", mock_nodegraph),
                ("image_filter", mock_image_filter),
                ("embedding", mock_embedding),
                ("lora", mock_lora),
                ("canvas", mock_canvas),
                ("chatbot", mock_chatbot),
                ("sounddevice_manager", mock_sound_manager),
            ]

            for attr_name, mock_service in services:
                assert hasattr(api_manager, attr_name)
                assert getattr(api_manager, attr_name) == mock_service.return_value

    def test_multiple_api_manager_instances(self, mock_emit_signal):
        """Test that multiple APIManager instances can be created independently"""
        mock_emit_signal_2 = MagicMock()

        with patch("airunner.api.api_manager.LLMAPIService") as mock_llm, patch(
            "airunner.api.api_manager.ARTAPIService"
        ) as mock_art, patch(
            "airunner.api.api_manager.TTSAPIService"
        ) as mock_tts, patch(
            "airunner.api.api_manager.STTAPIService"
        ) as mock_stt, patch(
            "airunner.api.api_manager.VideoAPIService"
        ) as mock_video, patch(
            "airunner.api.api_manager.NodegraphAPIService"
        ) as mock_nodegraph, patch(
            "airunner.api.api_manager.ImageFilterAPIServices"
        ) as mock_image_filter, patch(
            "airunner.api.api_manager.EmbeddingAPIServices"
        ) as mock_embedding, patch(
            "airunner.api.api_manager.LoraAPIServices"
        ) as mock_lora, patch(
            "airunner.api.api_manager.CanvasAPIService"
        ) as mock_canvas, patch(
            "airunner.api.api_manager.ChatbotAPIService"
        ) as mock_chatbot, patch(
            "airunner.api.api_manager.SoundDeviceManager"
        ) as mock_sound_manager:

            api_manager_1 = APIManager(emit_signal=mock_emit_signal)
            api_manager_2 = APIManager(emit_signal=mock_emit_signal_2)

            # Verify instances are independent
            assert api_manager_1 is not api_manager_2
            assert api_manager_1._emit_signal is mock_emit_signal
            assert api_manager_2._emit_signal is mock_emit_signal_2
            assert api_manager_1._emit_signal is not api_manager_2._emit_signal

            # Verify that each service class was called twice (once for each manager)
            assert mock_llm.call_count == 2
            assert mock_art.call_count == 2
            assert mock_chatbot.call_count == 2

            # Verify that each manager was initialized with its respective emit_signal
            llm_calls = mock_llm.call_args_list
            art_calls = mock_art.call_args_list

            # Check that the first calls (for api_manager_1) used mock_emit_signal
            assert llm_calls[0][1]["emit_signal"] is mock_emit_signal
            assert art_calls[0][1]["emit_signal"] is mock_emit_signal

            # Check that the second calls (for api_manager_2) used mock_emit_signal_2
            assert llm_calls[1][1]["emit_signal"] is mock_emit_signal_2
            assert art_calls[1][1]["emit_signal"] is mock_emit_signal_2

    def test_service_initialization_with_service_failure(self, mock_emit_signal):
        """Test APIManager behavior when a service fails to initialize"""
        # Mock all services except one that will fail
        with patch("airunner.api.api_manager.LLMAPIService") as mock_llm, patch(
            "airunner.api.api_manager.ARTAPIService"
        ) as mock_art, patch(
            "airunner.api.api_manager.TTSAPIService"
        ) as mock_tts, patch(
            "airunner.api.api_manager.STTAPIService"
        ) as mock_stt, patch(
            "airunner.api.api_manager.VideoAPIService"
        ) as mock_video, patch(
            "airunner.api.api_manager.NodegraphAPIService"
        ) as mock_nodegraph, patch(
            "airunner.api.api_manager.ImageFilterAPIServices"
        ) as mock_image_filter, patch(
            "airunner.api.api_manager.EmbeddingAPIServices"
        ) as mock_embedding, patch(
            "airunner.api.api_manager.LoraAPIServices"
        ) as mock_lora, patch(
            "airunner.api.api_manager.CanvasAPIService"
        ) as mock_canvas, patch(
            "airunner.api.api_manager.ChatbotAPIService"
        ) as mock_chatbot, patch(
            "airunner.api.api_manager.SoundDeviceManager"
        ) as mock_sound_manager:

            # Make one service fail during initialization
            mock_art.side_effect = Exception("Service initialization failed")

            # This should raise the exception from the failing service
            with pytest.raises(Exception, match="Service initialization failed"):
                APIManager(emit_signal=mock_emit_signal)

    def test_emit_signal_passed_correctly_to_all_services(self, mock_emit_signal):
        """Test that the same emit_signal instance is passed to all services"""
        captured_emit_signals = {}

        def capture_emit_signal(service_name):
            def mock_service(*args, **kwargs):
                captured_emit_signals[service_name] = kwargs.get("emit_signal")
                return MagicMock()

            return mock_service

        with patch(
            "airunner.api.api_manager.LLMAPIService",
            side_effect=capture_emit_signal("llm"),
        ), patch(
            "airunner.api.api_manager.ARTAPIService",
            side_effect=capture_emit_signal("art"),
        ), patch(
            "airunner.api.api_manager.TTSAPIService",
            side_effect=capture_emit_signal("tts"),
        ), patch(
            "airunner.api.api_manager.STTAPIService",
            side_effect=capture_emit_signal("stt"),
        ), patch(
            "airunner.api.api_manager.VideoAPIService",
            side_effect=capture_emit_signal("video"),
        ), patch(
            "airunner.api.api_manager.NodegraphAPIService",
            side_effect=capture_emit_signal("nodegraph"),
        ), patch(
            "airunner.api.api_manager.ImageFilterAPIServices",
            side_effect=capture_emit_signal("image_filter"),
        ), patch(
            "airunner.api.api_manager.EmbeddingAPIServices",
            side_effect=capture_emit_signal("embedding"),
        ), patch(
            "airunner.api.api_manager.LoraAPIServices",
            side_effect=capture_emit_signal("lora"),
        ), patch(
            "airunner.api.api_manager.CanvasAPIService",
            side_effect=capture_emit_signal("canvas"),
        ), patch(
            "airunner.api.api_manager.ChatbotAPIService",
            side_effect=capture_emit_signal("chatbot"),
        ), patch(
            "airunner.api.api_manager.SoundDeviceManager"
        ):

            APIManager(emit_signal=mock_emit_signal)

            # Verify all services received the same emit_signal instance
            for service_name, captured_signal in captured_emit_signals.items():
                assert (
                    captured_signal is mock_emit_signal
                ), f"Service {service_name} did not receive correct emit_signal"
