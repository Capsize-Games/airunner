import unittest
from unittest.mock import patch, MagicMock
from PySide6.QtWidgets import QWidget, QApplication
from airunner.api import API
from airunner.enums import SignalCode, LLMActionType
from airunner.handlers.llm import LLMRequest, LLMResponse
from airunner.handlers.stablediffusion.image_request import ImageRequest


class TestAPI(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Create a real QApplication instance once for the entire test suite
        cls.qapp = QApplication([])

    @classmethod
    def tearDownClass(cls):
        # Clean up the QApplication instance after all tests
        cls.qapp.quit()

    def setUp(self):
        # Pass initialize_app=False to avoid starting the full application
        self.api = API(initialize_app=False, initialize_gui=False)
        # Mock the app and main_window attributes with a QWidget
        self.api.app = MagicMock()
        self.api.app.main_window = QWidget()

    @patch("airunner.api.create_worker")
    @patch("airunner.api.setup_database")
    def test_initialization(self, mock_setup_database, mock_create_worker):
        mock_worker = MagicMock()
        mock_create_worker.return_value = mock_worker

        api = API(initialize_app=True, initialize_gui=False)

        mock_setup_database.assert_called_once()
        mock_create_worker.assert_called_once()
        mock_worker.add_to_queue.assert_called_with("scan_for_models")

    @patch("airunner.api.API.emit_signal")
    def test_send_llm_request(self, mock_emit_signal):
        prompt = "Test prompt"
        llm_request = LLMRequest()
        action = LLMActionType.CHAT

        self.api.llm.send_request(
            prompt, llm_request, action, do_tts_reply=True
        )

        mock_emit_signal.assert_called_once_with(
            SignalCode.LLM_TEXT_GENERATE_REQUEST_SIGNAL,
            {
                "llm_request": True,
                "request_data": {
                    "action": action,
                    "prompt": prompt,
                    "llm_request": llm_request,
                    "do_tts_reply": True,
                },
            },
        )

    @patch("airunner.api.API.emit_signal")
    def test_send_tts_request(self, mock_emit_signal):
        response = LLMResponse()

        self.api.send_llm_text_streamed_signal(response)

        mock_emit_signal.assert_called_once_with(
            SignalCode.LLM_TEXT_STREAMED_SIGNAL, {"response": response}
        )

    @patch("airunner.api.API.emit_signal")
    def test_send_image_request(self, mock_emit_signal):
        image_request = ImageRequest()

        self.api.send_image_request(image_request)

        mock_emit_signal.assert_called_once_with(
            SignalCode.DO_GENERATE_SIGNAL, {"image_request": image_request}
        )

    @patch("airunner.api.render_ui_from_spec", autospec=True)
    @patch("PySide6.QtWidgets.QDialog.exec", autospec=True)
    def test_show_hello_world_window(self, mock_exec, mock_render_ui):
        self.api.show_hello_world_window()

        # Debugging: Print call arguments to verify invocation
        print("render_ui_from_spec call args:", mock_render_ui.call_args_list)
        print("QDialog.exec call args:", mock_exec.call_args_list)

        mock_render_ui.assert_called_once()
        mock_exec.assert_called_once()

    @patch("airunner.api.load_ui_file", autospec=True)
    @patch("PySide6.QtWidgets.QDialog.exec", autospec=True)
    def test_show_dynamic_ui(self, mock_exec, mock_load_ui):
        # Return a QWidget dynamically to ensure QApplication is initialized
        mock_load_ui.return_value = QWidget()

        ui_file_path = "test.ui"

        self.api.show_dynamic_ui(ui_file_path)

        # Debugging: Print call arguments to verify invocation
        print("load_ui_file call args:", mock_load_ui.call_args_list)
        print("QDialog.exec call args:", mock_exec.call_args_list)

        mock_load_ui.assert_called_once_with(ui_file_path, unittest.mock.ANY)
        mock_exec.assert_called_once()

    @patch("airunner.api.load_ui_from_string", autospec=True)
    @patch("PySide6.QtWidgets.QDialog.exec", autospec=True)
    def test_show_dynamic_ui_from_string(self, mock_exec, mock_load_ui):
        # Return a QWidget dynamically to ensure QApplication is initialized
        mock_load_ui.return_value = QWidget()

        ui_content = "<ui></ui>"
        data = {"ui_content": ui_content}

        self.api.show_dynamic_ui_from_string(data)

        # Debugging: Print call arguments to verify invocation
        print("load_ui_from_string call args:", mock_load_ui.call_args_list)
        print("QDialog.exec call args:", mock_exec.call_args_list)

        mock_load_ui.assert_called_once_with(
            ui_content, unittest.mock.ANY, unittest.mock.ANY
        )
        mock_exec.assert_called_once()


if __name__ == "__main__":
    unittest.main()
