import unittest
from unittest.mock import patch, MagicMock, PropertyMock

from airunner.aihandler.stablediffusion.sd_handler import SDHandler


class TestSDHandler(unittest.TestCase):
    mock_model = MagicMock()
    sd_handler = SDHandler()

    def setUp(self):
        pass

    def test_init(self):
        self.assertIsNotNone(self.sd_handler)

    @patch.object(SDHandler, 'ai_model_by_name', return_value=mock_model)
    def test_model_property(self, mock_ai_model_by_name):
        self.assertEqual(self.sd_handler.model, self.mock_model)
        mock_ai_model_by_name.assert_called_once()

    @patch.object(sd_handler, 'initialized', new_callable=PropertyMock)
    @patch.object(sd_handler, 'do_generate', new_callable=PropertyMock)
    @patch.object(sd_handler, 'do_set_seed', new_callable=PropertyMock)
    @patch.object(SDHandler, 'generator_sample')
    def test_run(self, mock_generator_sample, mock_do_set_seed, mock_do_generate, mock_initialized):
        # Arrange
        mock_initialized.return_value = False
        mock_do_generate.return_value = True
        mock_do_set_seed.return_value = True
        mock_generator_sample.return_value = {
            "nsfw_content_detected": False,
            "action": "txt2img",
            "outpaint_box_rect": []
        }
        self.sd_handler.run()
        mock_generator_sample.assert_called_once()

    @patch.object(sd_handler.sd_request, 'is_txt2img', new_callable=PropertyMock)
    def test_not_has_pipe(self, mock_is_txt2img):
        mock_is_txt2img.return_value = True
        self.sd_handler.txt2img = None
        self.assertFalse(self.sd_handler.has_pipe())

    @patch.object(sd_handler.sd_request, 'is_txt2img', new_callable=PropertyMock)
    def test_has_pipe(self, mock_is_txt2img):
        mock_is_txt2img.return_value = True
        self.sd_handler.txt2img = True
        self.assertTrue(self.sd_handler.has_pipe())

    @patch.object(sd_handler.sd_request, 'is_txt2img', new_callable=PropertyMock)
    def test_on_move_to_cpu(self, mock_is_txt2img):
        mock_is_txt2img.return_value = True
        self.sd_handler.txt2img = MagicMock()
        self.sd_handler.txt2img.device = MagicMock()
        self.sd_handler.txt2img.device.type = "cuda"
        self.sd_handler.on_move_to_cpu()
        self.assertTrue(self.sd_handler.moved_to_cpu)

    def test_on_interrupt_process_signal(self):
        self.sd_handler.do_interrupt = False
        self.sd_handler.on_interrupt_process_signal({})
        self.assertTrue(self.sd_handler.do_interrupt)


if __name__ == '__main__':
    unittest.main()
