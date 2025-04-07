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

    @patch("airunner.utils.models.scan_path_for_items.SettingsMixin")
    def test_scan_path_for_lora_no_files(self, mock_settings_mixin):
        """Test scanning for Lora models when no files exist."""
        # Setup mock for database operations
        mock_database = MagicMock()
        mock_database.session.query.return_value.all.return_value = []
        mock_settings_mixin.return_value = mock_database

        # Run the scan
        scan_result = scan_path_for_lora(self.base_path)

        # Verify no changes were made (no files to process)
        self.assertFalse(scan_result)
        mock_database.session.commit.assert_not_called()

    @patch("airunner.utils.models.scan_path_for_items.SettingsMixin")
    def test_scan_path_for_lora_new_file(self, mock_settings_mixin):
        """Test scanning for Lora models when new file is found."""
        # Create a test file
        lora_file_path = os.path.join(self.lora_path, "test_lora.safetensors")
        with open(lora_file_path, "w") as f:
            f.write("test content")

        # Setup mock for database operations
        mock_database = MagicMock()
        mock_database.session.query.return_value.all.return_value = []
        mock_database.get_lora_by_name.return_value = None
        mock_settings_mixin.return_value = mock_database

        # Run the scan
        scan_result = scan_path_for_lora(self.base_path)

        # Verify a new Lora was added
        self.assertTrue(scan_result)
        mock_database.session.add.assert_called_once()
        mock_database.session.commit.assert_called_once()

        # Verify the correct Lora object was created
        added_lora = mock_database.session.add.call_args[0][0]
        self.assertEqual(added_lora.name, "test_lora")
        self.assertEqual(added_lora.path, lora_file_path)
        self.assertEqual(added_lora.version, "v1.0")
        self.assertEqual(added_lora.scale, 1)
        self.assertFalse(added_lora.enabled)
        self.assertFalse(added_lora.loaded)
        self.assertEqual(added_lora.trigger_word, "")

    @patch("airunner.utils.models.scan_path_for_items.SettingsMixin")
    def test_scan_path_for_lora_delete_missing(self, mock_settings_mixin):
        """Test scanning for Lora models when a file is missing."""
        # Setup mock for database operations
        missing_lora = Lora(
            name="missing_lora",
            path="/nonexistent/path/missing_lora.safetensors",
            scale=1,
            enabled=True,
            loaded=True,
            trigger_word="test",
            version="v1.0",
        )

        mock_database = MagicMock()
        mock_database.session.query.return_value.all.return_value = [
            missing_lora
        ]
        mock_settings_mixin.return_value = mock_database

        # Run the scan
        scan_result = scan_path_for_lora(self.base_path)

        # Verify the missing Lora was deleted
        self.assertTrue(scan_result)
        mock_database.session.delete.assert_called_once_with(missing_lora)
        mock_database.session.commit.assert_called_once()

    @patch("airunner.utils.models.scan_path_for_items.SettingsMixin")
    def test_scan_path_for_lora_update_existing(self, mock_settings_mixin):
        """Test scanning for Lora models when a file needs to be updated."""
        # Create a test file
        lora_file_path = os.path.join(self.lora_path, "test_lora.safetensors")
        with open(lora_file_path, "w") as f:
            f.write("test content")

        # Create an existing Lora with different path
        existing_lora = Lora(
            name="test_lora",
            path="/old/path/test_lora.safetensors",
            scale=1,
            enabled=True,
            loaded=True,
            trigger_word="test",
            version="v0.9",
        )

        # Setup mock for database operations
        mock_database = MagicMock()
        mock_database.session.query.return_value.all.return_value = [
            existing_lora
        ]
        mock_database.get_lora_by_name.return_value = existing_lora
        mock_settings_mixin.return_value = mock_database

        # Run the scan
        scan_result = scan_path_for_lora(self.base_path)

        # Verify a new Lora was added (since path changed)
        self.assertTrue(scan_result)
        mock_database.session.add.assert_called_once()
        mock_database.session.commit.assert_called_once()

    @patch("airunner.utils.models.scan_path_for_items.SettingsMixin")
    def test_scan_path_for_embeddings_new_file(self, mock_settings_mixin):
        """Test scanning for embeddings when a new file is found."""
        # Create a test file
        embedding_file_path = os.path.join(
            self.embeddings_path, "test_embedding.pt"
        )
        with open(embedding_file_path, "w") as f:
            f.write("test content")

        # Setup mock for database operations
        mock_database = MagicMock()
        mock_database.session.query.return_value.all.return_value = []
        mock_database.get_embedding_by_name.return_value = None
        mock_settings_mixin.return_value = mock_database

        # Run the scan
        scan_result = scan_path_for_embeddings(self.base_path)

        # Verify a new embedding was added
        self.assertTrue(scan_result)
        mock_database.session.add.assert_called_once()
        mock_database.session.commit.assert_called_once()

        # Verify the correct Embedding object was created
        added_embedding = mock_database.session.add.call_args[0][0]
        self.assertEqual(added_embedding.name, "test_embedding")
        self.assertEqual(added_embedding.path, embedding_file_path)
        self.assertEqual(added_embedding.version, "v1.0")
        self.assertEqual(added_embedding.tags, "")
        self.assertFalse(added_embedding.active)
        self.assertEqual(added_embedding.trigger_word, "")

    @patch("airunner.utils.models.scan_path_for_items.SettingsMixin")
    def test_scan_path_for_embeddings_delete_missing(
        self, mock_settings_mixin
    ):
        """Test scanning for embeddings when a file is missing."""
        # Setup mock for database operations
        missing_embedding = Embedding(
            name="missing_embedding",
            path="/nonexistent/path/missing_embedding.pt",
            version="v1.0",
            tags="test",
            active=True,
            trigger_word="test",
        )

        mock_database = MagicMock()
        mock_database.session.query.return_value.all.return_value = [
            missing_embedding
        ]
        mock_settings_mixin.return_value = mock_database

        # Run the scan
        scan_result = scan_path_for_embeddings(self.base_path)

        # Verify the missing embedding was deleted
        self.assertTrue(scan_result)
        mock_database.session.delete.assert_called_once_with(missing_embedding)
        mock_database.session.commit.assert_called_once()

    @patch("airunner.utils.models.scan_path_for_items.SettingsMixin")
    def test_scan_path_for_multiple_file_extensions(self, mock_settings_mixin):
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

        # Setup mock for database operations
        mock_database = MagicMock()
        mock_database.session.query.return_value.all.return_value = []
        mock_database.get_lora_by_name.return_value = None
        mock_settings_mixin.return_value = mock_database

        # Run the scan
        scan_result = scan_path_for_lora(self.base_path)

        # Verify the correct files were processed (3 valid extensions, 1 ignored)
        self.assertTrue(scan_result)
        self.assertEqual(mock_database.session.add.call_count, 3)
        mock_database.session.commit.assert_called_once()


if __name__ == "__main__":
    unittest.main()
