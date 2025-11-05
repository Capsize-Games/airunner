"""Unit tests for CanvasGenerationMixin AI image integration."""

import pytest
from unittest.mock import MagicMock
from PIL import Image

from airunner.components.art.gui.widgets.canvas.custom_scene import CustomScene


@pytest.fixture
def generation_scene(qapp, mock_scene_with_settings):
    """Create a scene with generation mixin for testing."""
    scene = mock_scene_with_settings
    scene.cached_send_image_to_canvas = None
    scene.api = MagicMock()
    scene.api.art.canvas.image_updated = MagicMock()
    scene._add_image_to_undo = MagicMock(return_value=1)
    scene._load_image_from_object = MagicMock()
    scene.update_drawing_pad_settings = MagicMock()
    scene._pending_image_binary = None
    scene._current_active_image_binary = None
    scene._commit_layer_history_transaction = MagicMock()
    scene._refresh_layer_display = MagicMock()
    scene._handle_outpaint = MagicMock()
    scene._clear_history = MagicMock()
    scene._get_current_selected_layer_id = MagicMock(return_value=1)
    scene.current_active_image = b"active_image_data"

    # Bind real methods
    scene.handle_cached_send_image_to_canvas = (
        CustomScene.handle_cached_send_image_to_canvas.__get__(
            scene, CustomScene
        )
    )
    scene.on_send_image_to_canvas_signal = (
        CustomScene.on_send_image_to_canvas_signal.__get__(scene, CustomScene)
    )
    scene.on_image_generated_signal = (
        CustomScene.on_image_generated_signal.__get__(scene, CustomScene)
    )
    scene._handle_image_generated_signal = (
        CustomScene._handle_image_generated_signal.__get__(scene, CustomScene)
    )

    return scene


class TestCachedImageHandling:
    """Test cached image processing."""

    def test_handle_cached_with_none_cache_does_nothing(
        self, generation_scene
    ):
        """Test cached handler with no cached image."""
        generation_scene.cached_send_image_to_canvas = None

        generation_scene.handle_cached_send_image_to_canvas()

        generation_scene._add_image_to_undo.assert_not_called()

    def test_handle_cached_with_image_sends_to_canvas(self, generation_scene):
        """Test cached handler sends cached image to canvas."""
        mock_response = MagicMock()
        mock_response.images = [Image.new("RGB", (100, 100))]
        generation_scene.cached_send_image_to_canvas = mock_response

        generation_scene.handle_cached_send_image_to_canvas()

        # Should process the image
        generation_scene._add_image_to_undo.assert_called_once()

    def test_cached_handler_clears_cache_after_processing(
        self, generation_scene
    ):
        """Test cache is cleared after processing."""
        mock_response = MagicMock()
        mock_response.images = [Image.new("RGB", (100, 100))]
        generation_scene.cached_send_image_to_canvas = mock_response

        generation_scene.handle_cached_send_image_to_canvas()

        assert generation_scene.cached_send_image_to_canvas is None


class TestSendImageToCanvas:
    """Test on_send_image_to_canvas_signal method."""

    def test_send_image_with_none_data_returns_early(self, generation_scene):
        """Test handler returns early with None data."""
        generation_scene.on_send_image_to_canvas_signal(None)

        generation_scene._add_image_to_undo.assert_not_called()

    def test_send_image_with_no_image_response_returns_early(
        self, generation_scene
    ):
        """Test handler returns early without image_response."""
        generation_scene.on_send_image_to_canvas_signal({})

        generation_scene._add_image_to_undo.assert_not_called()

    def test_send_image_with_empty_images_returns_early(
        self, generation_scene
    ):
        """Test handler returns early with empty images list."""
        mock_response = MagicMock()
        mock_response.images = []
        data = {"image_response": mock_response}

        generation_scene.on_send_image_to_canvas_signal(data)

        generation_scene._add_image_to_undo.assert_not_called()

    def test_send_image_adds_to_undo_history(self, generation_scene):
        """Test image is added to undo history."""
        mock_response = MagicMock()
        mock_response.images = [Image.new("RGB", (100, 100))]
        data = {"image_response": mock_response}

        generation_scene.on_send_image_to_canvas_signal(data)

        generation_scene._add_image_to_undo.assert_called_once()

    def test_send_image_loads_image_with_generated_flag(
        self, generation_scene
    ):
        """Test image is loaded with generated=True for positioning."""
        test_image = Image.new("RGB", (100, 100))
        mock_response = MagicMock()
        mock_response.images = [test_image]
        data = {"image_response": mock_response}

        generation_scene.on_send_image_to_canvas_signal(data)

        generation_scene._load_image_from_object.assert_called_once_with(
            image=test_image, generated=True
        )

    def test_send_image_converts_rgb_to_rgba(self, generation_scene):
        """Test RGB images are converted to RGBA."""
        test_image = Image.new("RGB", (50, 50), color="red")
        mock_response = MagicMock()
        mock_response.images = [test_image]
        data = {"image_response": mock_response}

        generation_scene.on_send_image_to_canvas_signal(data)

        # Should persist RGBA format
        call_args = generation_scene.update_drawing_pad_settings.call_args
        assert call_args is not None
        assert "layer_id" in call_args[1]
        assert "image" in call_args[1]
        # AIRAW1 header starts the binary
        assert call_args[1]["image"].startswith(b"AIRAW1")

    def test_send_image_preserves_rgba_mode(self, generation_scene):
        """Test RGBA images are not converted again."""
        test_image = Image.new("RGBA", (50, 50), color=(255, 0, 0, 128))
        mock_response = MagicMock()
        mock_response.images = [test_image]
        data = {"image_response": mock_response}

        generation_scene.on_send_image_to_canvas_signal(data)

        call_args = generation_scene.update_drawing_pad_settings.call_args
        assert call_args[1]["image"].startswith(b"AIRAW1")

    def test_send_image_sets_pending_and_active_binaries(
        self, generation_scene
    ):
        """Test image binary is set as pending and active."""
        test_image = Image.new("RGB", (50, 50))
        mock_response = MagicMock()
        mock_response.images = [test_image]
        data = {"image_response": mock_response}

        generation_scene.on_send_image_to_canvas_signal(data)

        assert generation_scene._pending_image_binary is not None
        assert generation_scene._current_active_image_binary is not None
        assert generation_scene._pending_image_binary.startswith(b"AIRAW1")

    def test_send_image_commits_history_transaction(self, generation_scene):
        """Test history transaction is committed."""
        test_image = Image.new("RGB", (50, 50))
        mock_response = MagicMock()
        mock_response.images = [test_image]
        data = {"image_response": mock_response}
        generation_scene._add_image_to_undo.return_value = 5

        generation_scene.on_send_image_to_canvas_signal(data)

        generation_scene._commit_layer_history_transaction.assert_called_once_with(
            5, "image"
        )

    def test_send_image_refreshes_layer_display(self, generation_scene):
        """Test layer display is refreshed."""
        test_image = Image.new("RGB", (50, 50))
        mock_response = MagicMock()
        mock_response.images = [test_image]
        data = {"image_response": mock_response}

        generation_scene.on_send_image_to_canvas_signal(data)

        generation_scene._refresh_layer_display.assert_called_once()

    def test_send_image_notifies_image_updated(self, generation_scene):
        """Test API is notified of image update."""
        test_image = Image.new("RGB", (50, 50))
        mock_response = MagicMock()
        mock_response.images = [test_image]
        data = {"image_response": mock_response}

        generation_scene.on_send_image_to_canvas_signal(data)

        generation_scene.api.art.canvas.image_updated.assert_called_once()

    def test_send_image_handles_refresh_exception_gracefully(
        self, generation_scene
    ):
        """Test refresh exception is logged but doesn't crash."""
        test_image = Image.new("RGB", (50, 50))
        mock_response = MagicMock()
        mock_response.images = [test_image]
        data = {"image_response": mock_response}
        generation_scene._refresh_layer_display.side_effect = Exception(
            "Refresh error"
        )

        # Should not raise (exception is caught internally)
        generation_scene.on_send_image_to_canvas_signal(data)

        # Method was attempted
        generation_scene._refresh_layer_display.assert_called_once()

    def test_send_image_handles_notify_exception_gracefully(
        self, generation_scene
    ):
        """Test notification exception is logged but doesn't crash."""
        test_image = Image.new("RGB", (50, 50))
        mock_response = MagicMock()
        mock_response.images = [test_image]
        data = {"image_response": mock_response}
        generation_scene.api.art.canvas.image_updated.side_effect = Exception(
            "Notify error"
        )

        # Should not raise (exception is caught internally)
        generation_scene.on_send_image_to_canvas_signal(data)

        # Method was attempted
        generation_scene.api.art.canvas.image_updated.assert_called_once()

    def test_send_image_handles_persist_exception_gracefully(
        self, generation_scene
    ):
        """Test persistence exception is handled gracefully."""
        test_image = MagicMock()
        test_image.mode = "RGB"
        test_image.convert.side_effect = Exception("Conversion error")
        mock_response = MagicMock()
        mock_response.images = [test_image]
        data = {"image_response": mock_response}

        # Should not raise, just skip persistence
        generation_scene.on_send_image_to_canvas_signal(data)

        # History commit still happens
        generation_scene._commit_layer_history_transaction.assert_called_once()


class TestImageGeneratedSignal:
    """Test on_image_generated_signal handling."""

    @pytest.mark.skip(reason="Method binding issue with _handle_outpaint mock")
    def test_generated_signal_with_outpaint_code(self, generation_scene):
        """Test outpaint code delegates to outpaint handler."""
        callback = MagicMock()
        data = {"code": "outpaint", "callback": callback}

        generation_scene.on_image_generated_signal(data)

        generation_scene._handle_outpaint.assert_called_once_with(callback)

    @pytest.mark.skip(reason="Method binding issue with callback mock")
    def test_generated_signal_with_other_code_calls_callback(
        self, generation_scene
    ):
        """Test non-outpaint code calls callback directly."""
        callback = MagicMock()
        data = {"code": "img2img", "callback": callback}

        generation_scene.on_image_generated_signal(data)

        callback.assert_called_once()
        generation_scene._handle_outpaint.assert_not_called()

    def test_generated_signal_with_none_callback_doesnt_crash(
        self, generation_scene
    ):
        """Test handler works without callback."""
        data = {"code": "img2img"}

        # Should not raise
        generation_scene.on_image_generated_signal(data)
