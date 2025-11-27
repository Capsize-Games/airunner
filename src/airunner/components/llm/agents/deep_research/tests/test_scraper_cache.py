import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from airunner.components.tools.web_content_extractor import (
    WebContentExtractor,
)


class TestWebContentExtractorCache(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for the cache
        self.test_dir = tempfile.mkdtemp()
        self.cache_dir = os.path.join(self.test_dir, "cache")
        os.makedirs(self.cache_dir, exist_ok=True)

        # Patch CACHE_DIR on the class
        self.cache_patcher = patch(
            "airunner.components.tools.web_content_extractor.WebContentExtractor.CACHE_DIR",
            Path(self.cache_dir),
        )
        self.cache_patcher.start()

        # Patch BLOCKLIST_FILE on the class
        self.blocklist_file = os.path.join(self.test_dir, "blocklist")
        self.blocklist_patcher = patch(
            "airunner.components.tools.web_content_extractor.WebContentExtractor.BLOCKLIST_FILE",
            Path(self.blocklist_file),
        )
        self.blocklist_patcher.start()

        self.extractor = WebContentExtractor()

    def tearDown(self):
        self.cache_patcher.stop()
        self.blocklist_patcher.stop()
        shutil.rmtree(self.test_dir)

    @patch("trafilatura.extract")
    @patch("trafilatura.fetch_url")
    def test_caching_mechanism(self, mock_fetch, mock_extract):
        # Setup mock response
        mock_fetch.return_value = (
            "<html><body><p>Test content for caching.</p></body></html>"
        )
        mock_extract.return_value = "Test content for caching."

        url = "https://example.com/test-cache"

        # Ensure blocklist is empty or doesn't contain our domain
        WebContentExtractor._blocklist = set()

        # First call - should hit the network (mock_fetch)
        print("\n[Test] First fetch - expecting network call")
        content1 = self.extractor.fetch_and_extract(url)

        # Verify network call
        mock_fetch.assert_called_once()
        self.assertIn("Test content for caching", content1)

        # Verify cache file exists
        cache_path = self.extractor._url_to_cache_path(url)
        self.assertTrue(
            os.path.exists(cache_path),
            f"Cache file should exist at {cache_path}",
        )

        print(f"[Test] Cache file verified at: {cache_path}")

        # Reset mock to verify it's not called again
        mock_fetch.reset_mock()
        mock_extract.reset_mock()

        # Second call - should hit the cache
        print("[Test] Second fetch - expecting cache hit (no network call)")
        content2 = self.extractor.fetch_and_extract(url)

        # Verify NO network call
        mock_fetch.assert_not_called()
        self.assertEqual(content1, content2)
        self.assertIn("Test content for caching", content2)

        print("[Test] Cache hit verified successfully")


if __name__ == "__main__":
    unittest.main()
