import unittest
from unittest.mock import patch, PropertyMock

import torch

from airunner.enums import HandlerType
from src.airunner.aihandler.base_handler import BaseHandler


class TestBaseHandler(unittest.TestCase):
    def setUp(self):
        self.base_handler = BaseHandler()
        type(self.base_handler).settings = PropertyMock(return_value={
            "llm_generator_settings": {"dtype": '32bit', "use_cuda": True},
            "use_cuda": True
        })

    @patch('src.airunner.aihandler.base_handler.get_torch_device')
    def test_device_property(self, mock_get_torch_device):
        mock_get_torch_device.return_value = 'cpu'
        self.assertEqual(self.base_handler.device, 'cpu')

    def test_llm_dtype_property(self):
        self.assertEqual(self.base_handler.llm_dtype, '32bit')

    @patch('torch.cuda.is_available')
    def test_use_cuda_property_false(self, mock_cuda_available):
        self.base_handler.handler_type = HandlerType.TRANSFORMER
        self.base_handler.use_gpu = True
        mock_cuda_available.return_value = True
        self.assertEqual(self.base_handler.use_cuda, False)

    @patch('torch.cuda.is_available')
    def test_use_cuda_property_true(self, mock_cuda_available):
        self.base_handler.handler_type = HandlerType.TRANSFORMER
        self.base_handler.settings["llm_generator_settings"]["dtype"] = '4bit'
        self.base_handler.use_gpu = True
        mock_cuda_available.return_value = True
        self.assertEqual(self.base_handler.use_cuda, True)

    def test_cuda_index_property(self):
        self.assertEqual(self.base_handler.cuda_index, 0)

    @patch('torch.cuda.is_available')
    def test_torch_dtype_property(self, mock_cuda_available):
        mock_cuda_available.return_value = True
        self.assertEqual(self.base_handler.torch_dtype, torch.float32)


if __name__ == '__main__':
    unittest.main()
