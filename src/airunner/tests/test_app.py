# PATCH GUI ENTRY POINTS BEFORE ANY APP IMPORTS
import sys
from unittest.mock import MagicMock

# Patch only QApplication for headless safety in this file
sys.modules["PySide6.QtWidgets.QApplication"] = MagicMock()
# Do NOT patch airunner.app_installer or AppInstaller here; let real class be used in other test modules

# NOTE: DO NOT LAUNCH ANY GUI OR REAL APPLICATION IN THESE TESTS.
# All GUI entry points (AppInstaller, MainWindow, QApplication, etc.) must be patched in any test that could trigger them.
# This is required for CI/headless safety and to prevent blocking or instability.
#
# If you add a test that could launch a window, you MUST patch the relevant GUI classes/functions.
#
# See project TDD/testing guidelines for details.

import unittest
from unittest.mock import patch, MagicMock, PropertyMock, mock_open
import signal
import sys

from airunner.app import App
from PySide6 import QtCore


class TestApp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # No need to patch AppInstaller/QApplication here; already patched at the top of the file
        pass

    @classmethod
    def tearDownClass(cls):
        pass

    def setUp(self):
        """Set up common test variables."""
        self.mock_main_window_class = MagicMock()
        self.mock_window_class_params = {}
        # Ensure .api.llm is always a MagicMock with required methods
        self.mock_llm = MagicMock()
        self.mock_llm.send_request = MagicMock()
        self.mock_llm.reload_rag = MagicMock()
        self.mock_llm.clear_history = MagicMock()
        self.mock_llm.converation_deleted = MagicMock()
        self.mock_api = MagicMock(llm=self.mock_llm, nodegraph=MagicMock())

    @patch("airunner.app.os.path.isdir", return_value=True)
    @patch("airunner.app.LocalHttpServerThread")
    @patch("sys.exit")
    @patch("PySide6.QtWidgets.QApplication")
    @patch("airunner.app.MainWindow")
    @patch("PySide6.QtWidgets.QApplication.exec", return_value=0)
    def test_show_main_application(
        self,
        mock_qapplication_exec,
        mock_main_window,
        mock_qapplication,
        mock_exit,
        mock_http_server,
        mock_isdir,
    ):
        """Test the show_main_application method."""
        app = App(initialize_gui=False)  # Prevent GUI from opening
        app.splash = mock_qapplication
        app.show_main_application(app)
        mock_main_window.assert_not_called()  # Ensure main window is not created
        mock_qapplication.finish.assert_not_called()  # Ensure splash screen is not finished

    def test_ensure_mathjax_already_present(self):
        """Test _ensure_mathjax when MathJax is already present (no setup needed)."""
        with patch("airunner.app.os.path.exists", return_value=True), patch.dict(
            "os.environ", {"QT_QPA_PLATFORM": "offscreen"}
        ):
            app = App(initialize_gui=False)
            with patch("airunner.app.subprocess.check_call") as mock_subproc:
                app._ensure_mathjax()
                mock_subproc.assert_not_called()

    def test_ensure_mathjax_triggers_setup(self):
        """Test _ensure_mathjax triggers setup when MathJax is missing."""
        with patch("airunner.app.os.path.exists", return_value=False), patch.dict(
            "os.environ", {"QT_QPA_PLATFORM": "offscreen"}
        ):
            app = App(initialize_gui=False)
            with patch("airunner.app.subprocess.check_call") as mock_subproc:
                mock_subproc.return_value = 0
                app._ensure_mathjax()
                mock_subproc.assert_called_once()

    def test_ensure_mathjax_setup_fails(self):
        """Test _ensure_mathjax raises RuntimeError if setup fails."""
        with patch("airunner.app.os.path.exists", return_value=False), patch.dict(
            "os.environ", {"QT_QPA_PLATFORM": "offscreen"}
        ):
            app = App(initialize_gui=False)
            with patch(
                "airunner.app.subprocess.check_call",
                side_effect=Exception("fail"),
            ):
                with self.assertRaises(RuntimeError) as ctx:
                    app._ensure_mathjax()
                assert "MathJax is required" in str(ctx.exception)

    def test_should_run_setup_wizard_true(self):
        """Test should_run_setup_wizard returns True when setup is needed."""
        with patch("airunner.app.AIRUNNER_DISABLE_SETUP_WIZARD", False), patch(
            "airunner.app.ApplicationSettings.objects.first",
            return_value=MagicMock(run_setup_wizard=True),
        ), patch(
            "airunner.app.PathSettings.objects.first",
            return_value=MagicMock(base_path="/tmp/airunner-test-path"),
        ), patch(
            "airunner.app.os.path.exists", return_value=False
        ):
            from airunner.app import App

            assert App.should_run_setup_wizard() is True

    def test_should_run_setup_wizard_false(self):
        """Test should_run_setup_wizard returns False when setup is not needed."""
        with patch("airunner.app.AIRUNNER_DISABLE_SETUP_WIZARD", False), patch(
            "airunner.app.ApplicationSettings.objects.first",
            return_value=MagicMock(run_setup_wizard=False),
        ), patch(
            "airunner.app.PathSettings.objects.first",
            return_value=MagicMock(base_path="/tmp/airunner-test-path"),
        ), patch(
            "airunner.app.os.path.exists", return_value=True
        ):
            from airunner.app import App

            assert App.should_run_setup_wizard() is False

    def test_run_setup_wizard_only_launches_gui_if_needed(self):
        """Test run_setup_wizard only launches AppInstaller if needed. AppInstaller must always be patched!"""
        # Patch AppInstaller and QApplication at the exact location used in App
        with patch("airunner.app_installer.AppInstaller") as mock_installer, patch(
            "PySide6.QtWidgets.QApplication"
        ) as mock_qapp:
            with patch("airunner.app.App.should_run_setup_wizard", return_value=True):
                from airunner.app import App

                App.run_setup_wizard()
                mock_installer.assert_called_once()
                mock_qapp.assert_not_called()  # Ensure QApplication is not created
        with patch("airunner.app_installer.AppInstaller") as mock_installer, patch(
            "PySide6.QtWidgets.QApplication"
        ) as mock_qapp:
            with patch("airunner.app.App.should_run_setup_wizard", return_value=False):
                from airunner.app import App

                App.run_setup_wizard()
                mock_installer.assert_not_called()
                mock_qapp.assert_not_called()  # Ensure QApplication is not created

    def test_run_setup_wizard_raises_if_not_patched(self):
        """Test that AppInstaller is never called unpatched: forcibly patch and assert, do not allow real window launch."""
        with patch(
            "airunner.app_installer.AppInstaller",
            side_effect=Exception(
                "AppInstaller should never be called unpatched in tests!"
            ),
        ) as mock_installer, patch("PySide6.QtWidgets.QApplication") as mock_qapp:
            with patch("airunner.app.App.should_run_setup_wizard", return_value=True):
                from airunner.app import App

                with self.assertRaises(Exception) as ctx:
                    App.run_setup_wizard()
                assert "AppInstaller should never be called unpatched" in str(
                    ctx.exception
                )
                mock_qapp.assert_not_called()  # Ensure QApplication is not created
