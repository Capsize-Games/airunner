import unittest
from unittest.mock import patch, MagicMock

from PySide6.QtWidgets import QTabWidget, QApplication, QWidget

from airunner.data.models.tab import Tab


class TestTabModel(unittest.TestCase):
    """Test cases for the Tab model class."""

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

    def test_tab_model_attributes(self):
        """Test Tab model attributes and default values."""
        # Create a new Tab instance
        tab = Tab(
            section="",
            name="",
            active=False,
            displayed=True,
            index=0
        )
        
        # Verify attributes exist and have correct default values
        self.assertEqual(tab.section, "")
        self.assertEqual(tab.name, "")
        self.assertFalse(tab.active)
        self.assertTrue(tab.displayed)
        self.assertEqual(tab.index, 0)

    def test_tab_model_creation_with_values(self):
        """Test Tab model creation with specified values."""
        # Create a Tab with specific values
        tab = Tab(
            section="test_section",
            name="Test Tab",
            active=True,
            displayed=False,
            index=3
        )
        
        # Verify attributes have the specified values
        self.assertEqual(tab.section, "test_section")
        self.assertEqual(tab.name, "Test Tab")
        self.assertTrue(tab.active)
        self.assertFalse(tab.displayed)
        self.assertEqual(tab.index, 3)

    @patch('airunner.data.models.tab.session_scope')
    def test_update_tabs_sets_active_tab(self, mock_session_scope):
        """Test update_tabs method correctly updates active tab state."""
        # Create mock session and related objects
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_update = MagicMock()
        
        # Configure mocks for the session query chain
        mock_session_context = MagicMock()
        mock_session_context.__enter__.return_value = mock_session
        mock_session_scope.return_value = mock_session_context
        
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.update.return_value = mock_update
        
        # Create a mock QTabWidget
        tab_widget = QTabWidget()
        tab_widget.addTab(QWidget(), "Tab 1")
        tab_widget.addTab(QWidget(), "Tab 2")
        tab_widget.addTab(QWidget(), "Tab 3")
        
        # Call the update_tabs method
        section = "test_section"
        index = 1  # Select "Tab 2"
        Tab.update_tabs(section, tab_widget, index)
        
        # Verify the first query sets all tabs in section to inactive
        first_call_args = mock_query.filter.call_args_list[0][0]
        self.assertEqual(len(first_call_args), 1)
        self.assertEqual(first_call_args[0].right.value, section)
        
        first_update_args = mock_filter.update.call_args_list[0][0]
        self.assertEqual(first_update_args[0], {"active": False})
        
        # Verify the second query sets the selected tab to active
        second_call_args = mock_query.filter.call_args_list[1][0]
        self.assertEqual(len(second_call_args), 2)
        self.assertEqual(second_call_args[0].right.value, section)
        self.assertEqual(second_call_args[1].right.value, "Tab 2")  # Tab text at index 1
        
        second_update_args = mock_filter.update.call_args_list[1][0]
        self.assertEqual(second_update_args[0], {"active": True})

    @patch('airunner.data.models.tab.session_scope')
    def test_update_tabs_with_empty_widget(self, mock_session_scope):
        """Test update_tabs with an empty QTabWidget."""
        # Create mock session
        mock_session = MagicMock()
        mock_session_context = MagicMock()
        mock_session_context.__enter__.return_value = mock_session
        mock_session_scope.return_value = mock_session_context
        
        # Create an empty QTabWidget
        tab_widget = QTabWidget()
        
        # Call the update_tabs method with an invalid index
        section = "test_section"
        index = 0  # Invalid index for empty widget
        
        # This should handle the error gracefully
        with self.assertRaises(IndexError):
            Tab.update_tabs(section, tab_widget, index)
        
        # Verify session.query was not called
        mock_session.query.assert_not_called()

    @patch('airunner.data.models.tab.session_scope')
    def test_update_tabs_with_invalid_index(self, mock_session_scope):
        """Test update_tabs with an invalid index."""
        # Create mock session
        mock_session = MagicMock()
        mock_session_context = MagicMock()
        mock_session_context.__enter__.return_value = mock_session
        mock_session_scope.return_value = mock_session_context
        
        # Create a QTabWidget with tabs
        tab_widget = QTabWidget()
        tab_widget.addTab(QWidget(), "Tab 1")
        tab_widget.addTab(QWidget(), "Tab 2")
        
        # Call the update_tabs method with an invalid index
        section = "test_section"
        index = 10  # Out of range
        
        # This should handle the error gracefully
        with self.assertRaises(IndexError):
            Tab.update_tabs(section, tab_widget, index)
        
        # Verify session.query was not called
        mock_session.query.assert_not_called()


if __name__ == "__main__":
    unittest.main()