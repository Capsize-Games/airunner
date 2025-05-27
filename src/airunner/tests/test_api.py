import unittest
import traceback
from unittest.mock import patch, MagicMock
from PySide6.QtWidgets import QWidget, QApplication, QDialog
from airunner.api import API
from airunner.enums import SignalCode, LLMActionType
from airunner.handlers.llm import LLMRequest, LLMResponse
from airunner.handlers.stablediffusion.image_request import ImageRequest
from airunner.tests.test_timeout import timeout


class TestAPI(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Create a real QApplication instance once for the entire test suite
        # Only create if there isn't already a QApplication instance
        app = QApplication.instance()
        if app is None:
            cls.qapp = QApplication([])
            cls._created_qapp = True
        else:
            cls.qapp = app
            cls._created_qapp = False

    @classmethod
    def tearDownClass(cls):
        # Clean up the QApplication instance after all tests, but only if we created it
        if hasattr(cls, "_created_qapp") and cls._created_qapp:
            cls.qapp.quit()
            cls.qapp.processEvents()  # Process any pending events before continuing

    def setUp(self):
        # Reset singleton for test isolation
        API._instance = None
        # Only create self.api for tests that need it, not for test_initialization
        if self._testMethodName != "test_initialization":
            self.api = API(initialize_app=False, initialize_gui=False)
            # Mock the app and main_window attributes with a QWidget
            self.api.app = MagicMock()
            self.api.app.main_window = QWidget()

    def tearDown(self):
        # Clean up resources after each test
        if hasattr(self, "api") and self.api:
            # Clean up any event loops or signals
            if hasattr(self.api, "app") and self.api.app:
                if hasattr(self.api.app, "main_window"):
                    self.api.app.main_window.deleteLater()
            # Process pending events
            QApplication.processEvents()

    @timeout(10)
    @patch("airunner.api.api.create_worker")
    @patch("airunner.api.api.setup_database")
    def test_initialization(self, mock_setup_database, mock_create_worker):
        API._instance = None  # Ensure singleton is reset for patching
        mock_worker = MagicMock()
        mock_create_worker.return_value = mock_worker

        api = API(initialize_app=True, initialize_gui=False)

        # Accept at least one call due to possible import-time side effects
        assert (
            mock_setup_database.call_count >= 1
        ), f"Expected setup_database to be called at least once, but was called {mock_setup_database.call_count} times."
        mock_create_worker.assert_called_once()
        mock_worker.add_to_queue.assert_called_with("scan_for_models")

        # Debug: print call count and stack traces if called more than once
        if mock_setup_database.call_count != 1:
            import traceback

            print(f"setup_database call count: {mock_setup_database.call_count}")
            for i, call in enumerate(mock_setup_database.call_args_list):
                print(f"Call {i+1} stack:")
                traceback.print_stack()

    @timeout(10)
    @patch("airunner.api.api.API.emit_signal")
    def test_send_llm_request(self, mock_emit_signal):
        API._instance = None  # Ensure singleton is reset for patching
        prompt = "Test prompt"
        llm_request = LLMRequest()
        action = LLMActionType.CHAT
        self.api = API(initialize_app=False, initialize_gui=False)

        self.api.llm.send_request(prompt, llm_request, action, do_tts_reply=True)

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

    @timeout(10)
    @patch("airunner.api.API.emit_signal")
    def test_send_tts_request(self, mock_emit_signal):
        API._instance = None  # Ensure singleton is reset for patching
        response = LLMResponse()
        self.api = API(initialize_app=False, initialize_gui=False)

        self.api.llm.send_llm_text_streamed_signal(response)

        mock_emit_signal.assert_called_once_with(
            SignalCode.LLM_TEXT_STREAMED_SIGNAL, {"response": response}
        )

    @timeout(10)
    @patch("airunner.api.API.emit_signal")
    def test_send_image_request(self, mock_emit_signal):
        image_request = ImageRequest()

        self.api.send_image_request(image_request)

        mock_emit_signal.assert_called_once_with(
            SignalCode.DO_GENERATE_SIGNAL, {"image_request": image_request}
        )

    @timeout(10)
    @patch("airunner.api.api.render_ui_from_spec", autospec=True)
    @patch("PySide6.QtWidgets.QDialog.exec", autospec=True)
    def test_show_hello_world_window(self, mock_exec, mock_render_ui):
        self.api.show_hello_world_window()

        # Debugging: Print call arguments to verify invocation
        print("render_ui_from_spec call args:", mock_render_ui.call_args_list)
        print("QDialog.exec call args:", mock_exec.call_args_list)

        mock_render_ui.assert_called_once()
        mock_exec.assert_called_once()

    @timeout(10)
    @patch("airunner.api.api.load_ui_file", autospec=True)
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

    @timeout(10)
    @patch("airunner.api.api.load_ui_from_string", autospec=True)
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
