import unittest
from unittest.mock import MagicMock, patch
from airunner.aihandler.mixins.embedding_mixin import EmbeddingMixin

class TestEmbeddingMixin(unittest.TestCase):
    def setUp(self):
        self.mixin = EmbeddingMixin()
        self.mixin.settings = {
            "embeddings": {
                "v1": [
                    {"name": "embed1", "path": "~/embed1.pt", "active": True},
                    {"name": "embed2", "path": "~/embed2.pt", "active": False}
                ]
            },
            "generator_settings": {"version": "v1"}
        }
        self.mixin.logger = MagicMock()
        self.mixin.pipe = MagicMock()

    def test_available_embeddings(self):
        expected = [
            {"name": "embed1", "path": "~/embed1.pt", "active": True},
            {"name": "embed2", "path": "~/embed2.pt", "active": False}
        ]
        self.assertEqual(self.mixin.available_embeddings, expected)

    @patch('os.path.exists', return_value=True)
    @patch('os.path.expanduser', side_effect=lambda x: x)
    def test_load_learned_embed_in_clip_load_active(self, mock_expanduser, mock_exists):
        self.mixin.load_learned_embed_in_clip()
        self.mixin.pipe.load_textual_inversion.assert_called_once_with("~/embed1.pt", token="embed1", weight_name="~/embed1.pt")
        self.mixin.pipe.unload_textual_inversion.assert_called_once_with("embed2")

    @patch('os.path.exists', return_value=False)
    @patch('os.path.expanduser', side_effect=lambda x: x)
    def test_load_learned_embed_in_clip_active_not_exists(self, mock_expanduser, mock_exists):
        self.mixin.load_learned_embed_in_clip()
        self.mixin.pipe.load_textual_inversion.assert_not_called()
        self.mixin.pipe.unload_textual_inversion.assert_called_once_with("embed2")

    @patch('os.path.exists', return_value=True)
    @patch('os.path.expanduser', side_effect=lambda x: x)
    def test_load_learned_embed_in_clip_load_exception(self, mock_expanduser, mock_exists):
        self.mixin.pipe.load_textual_inversion.side_effect = Exception("Load error")
        self.mixin.load_learned_embed_in_clip()
        self.mixin.logger.error.assert_any_call("Failed to load embedding embed1: Load error")

    def test_load_learned_embed_in_clip_unload_exception(self):
        self.mixin.pipe.unload_textual_inversion.side_effect = ValueError("Unload error")
        self.mixin.load_learned_embed_in_clip()
        self.mixin.logger.error.assert_any_call("Failed to unload embedding embed2: Unload error")

if __name__ == '__main__':
    unittest.main()
