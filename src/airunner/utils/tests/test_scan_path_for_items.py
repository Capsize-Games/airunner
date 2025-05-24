import unittest
import os
from unittest.mock import patch, MagicMock, mock_open
import tempfile
import shutil

from airunner.utils.models.scan_path_for_items import (
    scan_path_for_lora,
    scan_path_for_embeddings,
)
from airunner.data.models import Lora, Embedding


class TestScanPathForItems(unittest.TestCase):
    """Test cases for scanning paths for Lora and Embedding items."""

    def setUp(self):
        """Set up the test environment."""
        # Create a temporary directory structure for testing
        self.temp_dir = tempfile.mkdtemp()

        # Mock paths for test data
        self.base_path = self.temp_dir
        self.models_path = os.path.join(self.base_path, "art", "models")
        self.version_dir = os.path.join(self.models_path, "v1.0")
        self.lora_path = os.path.join(self.version_dir, "lora")
        self.embeddings_path = os.path.join(self.version_dir, "embeddings")

        # Create directory structure
        try:
            os.makedirs(self.lora_path, exist_ok=True)
        except FileExistsError:
            pass
        try:
            os.makedirs(self.embeddings_path, exist_ok=True)
        except FileExistsError:
            pass

    def tearDown(self):
        """Clean up after tests."""
        # Remove temporary directory and all contents
        shutil.rmtree(self.temp_dir)

    @patch("airunner.data.models.Lora.objects")
    def test_scan_path_for_lora_no_files(self, mock_lora_objects):
        """Test scanning for Lora models when no files exist."""
        mock_lora_objects.all.return_value = []
        scan_result = scan_path_for_lora(self.base_path)
        self.assertFalse(scan_result)

    @patch("airunner.data.models.Lora.objects")
    def test_scan_path_for_lora_new_file(self, mock_lora_objects):
        """Test scanning for Lora models when new file is found."""
        # Create a test file
        lora_file_path = os.path.join(self.lora_path, "test_lora.safetensors")
        with open(lora_file_path, "w") as f:
            f.write("test content")

        mock_lora_objects.all.return_value = []
        mock_lora_objects.filter_first.return_value = None
        mock_lora_objects.create.return_value = MagicMock()

        # Run the scan
        scan_result = scan_path_for_lora(self.base_path)

        # Verify a new Lora was added
        self.assertTrue(scan_result)
        mock_lora_objects.create.assert_called_once()

    @patch("airunner.data.models.Lora.objects")
    def test_scan_path_for_lora_delete_missing(self, mock_lora_objects):
        """Test scanning for Lora models when a file is missing."""
        # Setup mock for database operations
        missing_lora = MagicMock()
        missing_lora.path = "/nonexistent/path/missing_lora.safetensors"
        mock_lora_objects.all.return_value = [missing_lora]
        mock_lora_objects.delete.return_value = None

        # Run the scan
        scan_result = scan_path_for_lora(self.base_path)

        # Verify the missing Lora was deleted
        self.assertTrue(scan_result)
        mock_lora_objects.delete.assert_called_once()

    @patch("airunner.data.models.Lora.objects")
    def test_scan_path_for_lora_update_existing(self, mock_lora_objects):
        """Test scanning for Lora models when a file needs to be updated."""
        # Create a test file
        lora_file_path = os.path.join(self.lora_path, "test_lora.safetensors")
        with open(lora_file_path, "w") as f:
            f.write("test content")

        # Create an existing Lora with different path
        existing_lora = MagicMock()
        existing_lora.name = "test_lora"
        existing_lora.path = "/old/path/test_lora.safetensors"
        existing_lora.version = "v0.9"

        mock_lora_objects.all.return_value = [existing_lora]
        mock_lora_objects.filter_first.return_value = existing_lora
        mock_lora_objects.create.return_value = MagicMock()

        # Run the scan
        scan_result = scan_path_for_lora(self.base_path)

        # Verify a new Lora was added (since path changed)
        self.assertTrue(scan_result)
        mock_lora_objects.create.assert_called_once()

    @patch("airunner.data.models.Embedding.objects")
    def test_scan_path_for_embeddings_new_file(self, mock_embedding_objects):
        """Test scanning for embeddings when a new file is found."""
        # Create a test file
        embedding_file_path = os.path.join(
            self.embeddings_path, "test_embedding.pt"
        )
        with open(embedding_file_path, "w") as f:
            f.write("test content")

        mock_embedding_objects.all.return_value = []
        mock_embedding_objects.filter_first.return_value = None
        mock_embedding_objects.create.return_value = MagicMock()

        # Run the scan
        scan_result = scan_path_for_embeddings(self.base_path)

        # Verify a new embedding was added
        self.assertTrue(scan_result)
        mock_embedding_objects.create.assert_called_once()

    @patch("airunner.data.models.Embedding.objects")
    def test_scan_path_for_embeddings_delete_missing(
        self, mock_embedding_objects
    ):
        """Test scanning for embeddings when a file is missing."""
        # Setup mock for database operations
        missing_embedding = MagicMock()
        missing_embedding.path = "/nonexistent/path/missing_embedding.pt"
        mock_embedding_objects.all.return_value = [missing_embedding]
        mock_embedding_objects.delete.return_value = None

        # Run the scan
        scan_result = scan_path_for_embeddings(self.base_path)

        # Verify the missing embedding was deleted
        self.assertTrue(scan_result)
        mock_embedding_objects.delete.assert_called_once()

    @patch("airunner.data.models.Lora.objects")
    def test_scan_path_for_multiple_file_extensions(self, mock_lora_objects):
        """Test scanning with multiple file extensions."""
        # Create test files with different extensions
        lora_file1 = os.path.join(self.lora_path, "test_lora1.safetensors")
        lora_file2 = os.path.join(self.lora_path, "test_lora2.ckpt")
        lora_file3 = os.path.join(self.lora_path, "test_lora3.pt")
        lora_file4 = os.path.join(
            self.lora_path, "test_lora4.txt"
        )  # Should be ignored

        for file_path in [lora_file1, lora_file2, lora_file3, lora_file4]:
            with open(file_path, "w") as f:
                f.write("test content")

        mock_lora_objects.all.return_value = []
        mock_lora_objects.filter_first.return_value = None
        mock_lora_objects.create.return_value = MagicMock()

        # Run the scan
        scan_result = scan_path_for_lora(self.base_path)

        # Verify the correct files were processed (3 valid extensions, 1 ignored)
        self.assertTrue(scan_result)
        self.assertEqual(mock_lora_objects.create.call_count, 3)


if __name__ == "__main__":
    unittest.main()
