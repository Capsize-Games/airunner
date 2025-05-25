import unittest
import os
from unittest.mock import patch, mock_open
from airunner.utils.application.get_version import get_version


class TestGetVersion(unittest.TestCase):
    """Test cases for the get_version utility function."""

    def setUp(self):
        """Set up test environment before each test."""
        # Save the current working directory
        self.original_cwd = os.getcwd()
        
        # Ensure any file mocks are reset
        self.patcher = None

    def tearDown(self):
        """Clean up after each test."""
        # Reset any active patches
        if self.patcher:
            self.patcher.stop()

    @patch("builtins.open", new_callable=mock_open, read_data="1.2.3")
    def test_get_version_from_version_file(self, mock_file):
        """Test retrieving version from VERSION file."""
        version = get_version()
        
        # Check that the function returns the correct version
        self.assertEqual(version, "1.2.3")
        
        # Verify the VERSION file was opened
        mock_file.assert_called_once_with("./VERSION", "r")

    @patch("builtins.open")
    def test_get_version_from_setup_py(self, mock_file):
        """Test retrieving version from setup.py in current directory."""
        # Mock the first open call to fail with FileNotFoundError
        mock_file.side_effect = [
            FileNotFoundError,  # VERSION file not found
            mock_open(read_data='setup(\n    name="airunner",\n    version="2.0.5",\n    description="AI Runner")').return_value
        ]
        
        version = get_version()
        
        # Check that the function returns the correct version
        self.assertEqual(version, "2.0.5")
        
        # Verify both files were tried
        self.assertEqual(mock_file.call_count, 2)
        mock_file.assert_any_call("./VERSION", "r")
        mock_file.assert_any_call("./setup.py", "r")

    @patch("builtins.open")
    def test_get_version_from_parent_setup_py(self, mock_file):
        """Test retrieving version from setup.py in parent directory."""
        # Mock multiple open calls with different results
        mock_file.side_effect = [
            FileNotFoundError,  # VERSION file not found
            FileNotFoundError,  # setup.py not found in current directory
            mock_open(read_data='setup(\n    name="airunner",\n    version="3.1.0",\n    description="AI Runner")').return_value
        ]
        
        version = get_version()
        
        # Check that the function returns the correct version
        self.assertEqual(version, "3.1.0")
        
        # Verify all three files were tried
        self.assertEqual(mock_file.call_count, 3)
        mock_file.assert_any_call("./VERSION", "r")
        mock_file.assert_any_call("./setup.py", "r")
        mock_file.assert_any_call("../../setup.py", "r")

    @patch("builtins.open")
    def test_get_version_strip_non_numeric(self, mock_file):
        """Test that non-numeric characters are removed from version."""
        # Return a version with quotes and whitespace
        mock_file.return_value = mock_open(read_data='"1.2.3-alpha"').return_value
        
        version = get_version()
        
        # Check that only numeric characters and dots remain
        self.assertEqual(version, "1.2.3")

    @patch("builtins.open")
    def test_get_version_all_files_missing(self, mock_file):
        """Test behavior when no version files are found."""
        # Mock all open calls to fail
        mock_file.side_effect = FileNotFoundError
        
        version = get_version()
        
        # Should return empty string when no files are found
        self.assertEqual(version, "")
        
        # Verify all three files were tried
        self.assertEqual(mock_file.call_count, 3)

    @patch("builtins.open")
    def test_get_version_malformed_setup_py(self, mock_file):
        """Test handling of malformed setup.py file."""
        # Mock a setup.py file with no version information
        mock_file.side_effect = [
            FileNotFoundError,  # VERSION file not found
            mock_open(read_data='setup(\n    name="airunner"\n)').return_value
        ]

        # Should handle IndexError from missing version and try next file
        version = get_version()

        # Should return empty string when parsing fails
        self.assertEqual(version, "")


if __name__ == "__main__":
    unittest.main()