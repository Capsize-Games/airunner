import unittest
from unittest.mock import MagicMock
from PySide6.QtWidgets import QWidget, QApplication

from airunner.base_plugin import BasePlugin


class TestBasePlugin(unittest.TestCase):
    """Test cases for the BasePlugin abstract base class."""

    @classmethod
    def setUpClass(cls):
        """Set up QApplication instance for the test suite."""
        if not QApplication.instance():
            cls.qapp = QApplication([])
        else:
            cls.qapp = QApplication.instance()

    @classmethod
    def tearDownClass(cls):
        """Clean up QApplication instance after tests."""
        cls.qapp.quit()

    def test_base_plugin_abstract_methods(self):
        """Test that BasePlugin enforces implementation of its abstract methods."""
        # Attempt to instantiate BasePlugin directly should fail
        with self.assertRaises(TypeError):
            BasePlugin()

    def test_base_plugin_implementation(self):
        """Test a concrete implementation of BasePlugin."""
        # Create a concrete implementation of BasePlugin
        class TestPlugin(BasePlugin):
            name = "Test Plugin"

            def get_widget(self):
                """Return a test widget."""
                return QWidget()

        # Instantiate the concrete implementation
        plugin = TestPlugin()
        
        # Verify plugin name
        self.assertEqual(plugin.name, "Test Plugin")
        
        # Verify get_widget method returns a QWidget
        widget = plugin.get_widget()
        self.assertIsInstance(widget, QWidget)

    def test_base_plugin_multiple_implementations(self):
        """Test multiple concrete implementations of BasePlugin."""
        class Plugin1(BasePlugin):
            name = "Plugin 1"
            
            def get_widget(self):
                widget = QWidget()
                widget.setObjectName("widget1")
                return widget

        class Plugin2(BasePlugin):
            name = "Plugin 2"
            
            def get_widget(self):
                widget = QWidget()
                widget.setObjectName("widget2")
                return widget

        # Create instances
        plugin1 = Plugin1()
        plugin2 = Plugin2()
        
        # Verify different names
        self.assertEqual(plugin1.name, "Plugin 1")
        self.assertEqual(plugin2.name, "Plugin 2")
        
        # Verify widgets have different object names
        widget1 = plugin1.get_widget()
        widget2 = plugin2.get_widget()
        self.assertEqual(widget1.objectName(), "widget1")
        self.assertEqual(widget2.objectName(), "widget2")


if __name__ == "__main__":
    unittest.main()