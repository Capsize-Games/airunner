import unittest
from unittest.mock import patch, MagicMock, PropertyMock, mock_open
import sys
import signal
from src.airunner.app import App

class TestApp(unittest.TestCase):
    def setUp(self):
        """Set up common test variables."""
        self.mock_main_window_class = MagicMock()
        self.mock_window_class_params = {}

    @patch("src.airunner.app.QApplication")
    @patch("sys.exit")
    def test_initialization_with_gui(self, mock_exit, mock_qapplication):
        """Test App initialization with GUI enabled."""
        mock_qapplication.return_value.exec.return_value = 0  # Prevent sys.exit from being called
        app = App(no_splash=True, initialize_gui=True)
        self.assertIsNotNone(app.app)
        mock_qapplication.assert_called_once()
        mock_exit.assert_called_once_with(0)  # Adjusted to expect sys.exit with 0

    def test_handle_upgrade(self):
        """Test the upgrade handling logic."""
        # Use context managers instead of decorators to avoid parameter ordering issues
        with patch("src.airunner.data.models.PipelineModel", new=MagicMock()) as mock_pipeline_model:
            with patch("src.airunner.app.os.makedirs") as mock_makedirs:
                with patch("src.airunner.data.bootstrap.pipeline_bootstrap_data.pipeline_bootstrap_data", 
                          new=MagicMock(return_value=[])) as mock_bootstrap:
                    # Mock open to prevent file operations
                    with patch("builtins.open", mock_open()):
                        # Use patch.object to mock the application_settings and path_settings
                        mock_app_settings = MagicMock()
                        mock_app_settings.app_version = "0.0.0"
                        mock_path_settings = MagicMock()
                        mock_path_settings.base_path = "/mock/path"
                        
                        with patch.object(App, 'application_settings', new_callable=PropertyMock) as mock_app_settings_prop:
                            with patch.object(App, 'path_settings', new_callable=PropertyMock) as mock_path_settings_prop:
                                mock_app_settings_prop.return_value = mock_app_settings
                                mock_path_settings_prop.return_value = mock_path_settings
                                mock_pipeline_model.objects.filter_by_first.return_value = None
                                
                                app = App(initialize_gui=False)
                                app.handle_upgrade("1.0.0")
                                mock_makedirs.assert_called()

    def test_signal_handler(self):
        """Test signal handler setup."""
        # Let's verify the signal handler exists and is callable
        app = App(initialize_gui=False)
        
        # Test that app.signal_handler exists and is a callable method
        self.assertTrue(hasattr(app, 'signal_handler'), "App should have a signal_handler attribute")
        self.assertTrue(callable(app.signal_handler), "App.signal_handler should be callable")
        
        # We can also test the basic behavior of the signal handler
        with patch('sys.exit') as mock_exit:
            # Call the signal handler with SIGINT signal
            app.signal_handler(signal.SIGINT, None)
            mock_exit.assert_called_once()

if __name__ == "__main__":
    unittest.main()