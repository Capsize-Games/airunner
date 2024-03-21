import unittest
from unittest.mock import MagicMock, patch
from airunner.aihandler.mixins.lora_mixin import LoraMixin


class TestLoraMixin(unittest.TestCase):
    def setUp(self):
        self.mixin = LoraMixin()
        self.mixin.settings = {
            "lora": [
                {
                    'name': "foobar",
                    'path': "bar",
                    'scale': 1,
                    'enabled': True,
                    'loaded': False,
                    'trigger_word': 'foo',
                    'version': '1.0',
                },
                {
                    'name': "lora",
                    'path': "bar",
                    'scale': 1,
                    'enabled': False,
                    'loaded': False,
                    'trigger_word': 'foo',
                    'version': '1.0',
                },
                {
                    'name': "disabled lora",
                    'path': "disabled/lora/path",
                    'scale': 1,
                    'enabled': True,
                    'loaded': False,
                    'trigger_word': 'foo',
                    'version': '1.0',
                }
            ],
            "path_settings": {"base_path": "/base", "lora_model_path": "lora"}
        }
        self.mixin.disabled_lora = ["disabled/lora/path"]
        self.mixin.model = {"version": "1.0"}
        self.mixin.logger = MagicMock()

    def test_available_lora(self):
        self.assertEqual(self.mixin.available_lora, {"1.0": [
            {
                'name': "foobar",
                'path': "bar",
                'scale': 1,
                'enabled': True,
                'loaded': False,
                'trigger_word': 'foo',
                'version': '1.0',
            },
            {
                'name': "lora",
                'path': "bar",
                'scale': 1,
                'enabled': False,
                'loaded': False,
                'trigger_word': 'foo',
                'version': '1.0',
            },
            {
                'name': "disabled lora",
                'path': "disabled/lora/path",
                'scale': 1,
                'enabled': True,
                'loaded': False,
                'trigger_word': 'foo',
                'version': '1.0',
            }
        ]})

    @patch('os.path.join')
    def test_add_lora_to_pipe(self, mock_join):
        self.mixin.apply_lora = MagicMock()
        self.mixin.add_lora_to_pipe()
        self.mixin.apply_lora.assert_called_once()

    @patch('os.path.join')
    @patch('os.walk')
    def test_apply_lora(self, mock_walk, mock_join):
        mock_walk.return_value = [("/base/lora", [], ["lora_weights"])]
        mock_join.return_value = "/base/lora/lora_weights"
        self.mixin.model = {
            "version": "1.0"
        }
        self.mixin.load_lora = MagicMock()
        self.mixin.apply_lora()
        self.mixin.load_lora.assert_called()

    @patch('os.walk')
    def test_apply_lora_with_file_starting_with_lora_name(self, mock_walk):
        mock_walk.return_value = [("/base/lora", [], ["lora_weights"])]
        self.mixin.settings = {
            "lora": [
                {"name": "lora", "enabled": True, "version": "1.0"}
            ],
            "path_settings": {"base_path": "/base", "lora_model_path": "lora"}
        }
        self.mixin.model = {"version": "1.0"}
        self.mixin.load_lora = MagicMock()
        self.mixin.apply_lora()
        self.mixin.load_lora.assert_called_once_with("/base/lora/lora_weights", {"name": "lora", "enabled": True, "version": "1.0"})

    @patch('os.path.join')
    def test_load_lora(self, mock_join):
        mock_join.return_value = "/base/lora/lora_weights"
        self.mixin.pipe = MagicMock()
        self.mixin.load_lora("/base/lora/lora_weights", {"name": "lora", "scale": 1.0})
        self.mixin.pipe.load_lora_weights.assert_called_once_with(".", weight_name="/base/lora/lora_weights")
        self.assertEqual(self.mixin.loaded_lora, [{"name": "lora", "scale": 1.0}])

    def test_load_lora_with_disabled_lora(self):
        checkpoint_path = "/base/lora/lora_weights"
        self.mixin.disabled_lora.append(checkpoint_path)
        self.mixin.pipe = MagicMock()
        self.mixin.load_lora(checkpoint_path, {"name": "lora", "scale": 1.0})
        self.assertEqual(self.mixin.pipe.load_lora_weights.call_count, 0)

    @patch('airunner.aihandler.mixins.lora_mixin.LoraMixin.disable_lora')
    def test_load_lora_with_attribute_error(self, mock_disable_lora):
        checkpoint_path = "/base/lora/lora_weights"
        lora = {"name": "lora", "scale": 1.0}
        self.mixin.pipe = MagicMock()
        self.mixin.pipe.load_lora_weights.side_effect = AttributeError("This model does not support LORA")
        self.mixin.load_lora(checkpoint_path, lora)
        mock_disable_lora.assert_called_once_with(checkpoint_path)
        self.assertNotIn(lora, self.mixin.loaded_lora)

    @patch('airunner.aihandler.mixins.lora_mixin.LoraMixin.disable_lora')
    def test_load_lora_with_runtime_error(self, mock_disable_lora):
        checkpoint_path = "/base/lora/lora_weights"
        lora = {"name": "lora", "scale": 1.0}
        self.mixin.pipe = MagicMock()
        self.mixin.pipe.load_lora_weights.side_effect = RuntimeError("LORA could not be loaded")
        self.mixin.load_lora(checkpoint_path, lora)
        mock_disable_lora.assert_called_once_with(checkpoint_path)
        self.assertNotIn(lora, self.mixin.loaded_lora)

    def test_disable_lora(self):
        self.mixin.disable_lora("/base/lora/lora_weights")
        self.assertEqual(self.mixin.disabled_lora, ['disabled/lora/path', '/base/lora/lora_weights'])

    def test_model_version_not_in_available_lora(self):
        self.mixin.load_lora = MagicMock()
        self.mixin.model = {"version": "2.0"}
        self.mixin.apply_lora()
        self.assertEqual(self.mixin.load_lora.call_count, 0)


if __name__ == '__main__':
    unittest.main()