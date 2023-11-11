import unittest

from airunner.aihandler.runner import SDRunner


class TestControlNetType(unittest.TestCase):
    def setUp(self):
        self.obj = SDRunner()  # Replace with your actual class name

    def test_controlnet_type(self):
        test_cases = {
            "canny": "lllyasviel/control_v11p_sd15_canny",
            "depth_leres": "lllyasviel/control_v11f1p_sd15_depth",
            "mlsd": "lllyasviel/control_v11p_sd15_mlsd",
        }

        for controlnet_type, expected in test_cases.items():
            self.obj.options["controlnet"] = controlnet_type
            self.assertEqual(self.obj.controlnet_model, expected)

    def test_unknown_controlnet_type(self):
        self.obj.options["controlnet"] = "unknown"
        with self.assertRaises(Exception):
            self.obj.controlnet_model

if __name__ == "__main__":
    unittest.main()