import os
import types
import unittest
from unittest.mock import patch

import airunner


class TestDiffusersRuntimeCompat(unittest.TestCase):
    def test_disables_torchao_for_problematic_dependency_pair(self):
        fake_import_utils = types.SimpleNamespace(
            _torchao_available=True,
            _torchao_version="0.16.0",
        )

        def fake_version(package_name: str) -> str:
            return {
                "diffusers": "0.35.1",
                "torchao": "0.16.0",
            }[package_name]

        with patch.dict(os.environ, {}, clear=True):
            with patch(
                "airunner.importlib_metadata.version",
                side_effect=fake_version,
            ):
                with patch(
                    "airunner.importlib.import_module",
                    return_value=fake_import_utils,
                ):
                    applied = airunner._apply_diffusers_torchao_workaround()

        self.assertTrue(applied)
        self.assertFalse(fake_import_utils._torchao_available)
        self.assertEqual(
            fake_import_utils._torchao_version,
            "disabled-by-airunner",
        )

    def test_respects_opt_in_override(self):
        fake_import_utils = types.SimpleNamespace(
            _torchao_available=True,
            _torchao_version="0.16.0",
        )

        with patch.dict(
            os.environ,
            {"AIRUNNER_ENABLE_DIFFUSERS_TORCHAO": "1"},
            clear=True,
        ):
            with patch(
                "airunner.importlib_metadata.version",
                side_effect=lambda package_name: {
                    "diffusers": "0.35.1",
                    "torchao": "0.16.0",
                }[package_name],
            ):
                with patch(
                    "airunner.importlib.import_module",
                    return_value=fake_import_utils,
                ):
                    applied = airunner._apply_diffusers_torchao_workaround()

        self.assertFalse(applied)
        self.assertTrue(fake_import_utils._torchao_available)

    def test_skips_unaffected_versions(self):
        fake_import_utils = types.SimpleNamespace(
            _torchao_available=True,
            _torchao_version="0.15.0",
        )

        with patch.dict(os.environ, {}, clear=True):
            with patch(
                "airunner.importlib_metadata.version",
                side_effect=lambda package_name: {
                    "diffusers": "0.36.0",
                    "torchao": "0.16.0",
                }[package_name],
            ):
                with patch(
                    "airunner.importlib.import_module",
                    return_value=fake_import_utils,
                ):
                    applied = airunner._apply_diffusers_torchao_workaround()

        self.assertFalse(applied)
        self.assertTrue(fake_import_utils._torchao_available)


if __name__ == "__main__":
    unittest.main()