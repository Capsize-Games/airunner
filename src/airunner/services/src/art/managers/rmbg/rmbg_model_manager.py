"""Service-owned BRIA RMBG model loading and inference."""

from __future__ import annotations

import importlib.machinery
import importlib.util
import logging
import os
import sys
from dataclasses import dataclass
from types import ModuleType

import torch
from PIL import Image
from safetensors.torch import load_file
from torchvision import transforms

from airunner_services.settings import MODELS_DIR
from airunner_services.utils.image.convert_image_to_binary import (
    convert_image_to_binary,
)
from airunner_services.utils.memory import clear_memory


@dataclass(frozen=True)
class RMBGModelSpec:
    """Describe the on-disk BRIA RMBG model bundle."""

    repo_id: str = "briaai/RMBG-2.0"
    model_dir_name: str = "RMBG-2.0"

    @property
    def local_dir(self) -> str:
        """Return the expected RMBG model directory."""
        return os.path.join(
            MODELS_DIR,
            "vision",
            "models",
            "rmbg",
            self.model_dir_name,
        )


class RMBGModelManager:
    """Load and run BRIA RMBG-2.0 from the local model bundle."""

    def __init__(self, spec: RMBGModelSpec | None = None) -> None:
        """Initialize the RMBG manager."""
        self.spec = spec or RMBGModelSpec()
        self._model = None
        self._device: str | None = None

    @property
    def is_loaded(self) -> bool:
        """Return whether the RMBG model is already resident."""
        return self._model is not None

    @property
    def model_id(self) -> str:
        """Return the shared identifier used for RMBG status tracking."""
        return self.spec.repo_id

    def required_files(self) -> list[str]:
        """Return the files needed for RMBG inference."""
        return [
            "config.json",
            "model.safetensors",
            "preprocessor_config.json",
            "BiRefNet_config.py",
            "birefnet.py",
        ]

    def missing_files(self) -> list[str]:
        """Return required files that are still missing from disk."""
        base_dir = self.spec.local_dir
        return [
            rel_path
            for rel_path in self.required_files()
            if not os.path.exists(os.path.join(base_dir, rel_path))
        ]

    def is_available_on_disk(self) -> bool:
        """Return True when every required model file exists."""
        return not self.missing_files()

    def _load(self) -> None:
        """Load the RMBG model from disk when required."""
        if self._model is not None:
            return

        self._device = self._pick_device()
        base_dir = self.spec.local_dir
        config_py = os.path.join(base_dir, "BiRefNet_config.py")
        model_py = os.path.join(base_dir, "birefnet.py")
        weights_path = os.path.join(base_dir, "model.safetensors")

        missing = [
            path
            for path in (
                "BiRefNet_config.py",
                "birefnet.py",
                "model.safetensors",
            )
            if not os.path.exists(os.path.join(base_dir, path))
        ]
        if missing:
            raise FileNotFoundError(
                f"Missing RMBG model files on disk: {missing}"
            )

        package_name = f"airunner_rmbg2_{abs(hash(base_dir))}"
        self._ensure_package(package_name, base_dir)
        config_module = self._load_submodule(
            package_name,
            "BiRefNet_config",
            config_py,
        )
        model_module = self._load_submodule(
            package_name,
            "birefnet",
            model_py,
        )

        config_class = getattr(config_module, "BiRefNetConfig", None)
        model_class = getattr(model_module, "BiRefNet", None)
        if config_class is None:
            raise ImportError(
                "RMBG config module does not define BiRefNetConfig"
            )
        if model_class is None:
            raise ImportError("RMBG model module does not define BiRefNet")

        config = config_class(bb_pretrained=False)
        model = model_class(config=config)
        state_dict = load_file(weights_path, device="cpu")
        model.load_state_dict(state_dict, strict=False)
        model = model.to(self._device)
        self._model = model.eval()

    def unload(self) -> None:
        """Release the loaded RMBG model and clear device memory."""
        model = self._model
        device = self._device
        self._model = None
        self._device = None

        if model is None:
            return

        try:
            model.cpu()
        except Exception:
            logging.getLogger(__name__).debug(
                "Failed to move RMBG model to CPU during unload",
                exc_info=True,
            )

        del model
        clear_memory(device)

        if device and device.startswith("cuda"):
            try:
                if hasattr(torch.cuda, "ipc_collect"):
                    torch.cuda.ipc_collect()
            except Exception:
                logging.getLogger(__name__).debug(
                    "Failed to clear CUDA cache while unloading RMBG",
                    exc_info=True,
                )

    @staticmethod
    def _ensure_package(package_name: str, base_dir: str) -> None:
        """Register a synthetic package for RMBG remote-code modules."""
        if package_name in sys.modules:
            return

        package = importlib.util.module_from_spec(
            importlib.machinery.ModuleSpec(
                package_name,
                loader=None,
                is_package=True,
            )
        )
        package.__path__ = [base_dir]  # type: ignore[attr-defined]
        sys.modules[package_name] = package

    @staticmethod
    def _load_submodule(
        package_name: str,
        module_name: str,
        file_path: str,
    ) -> ModuleType:
        """Load one RMBG remote-code module from the local bundle."""
        full_name = f"{package_name}.{module_name}"
        if full_name in sys.modules:
            return sys.modules[full_name]

        spec = importlib.util.spec_from_file_location(full_name, file_path)
        if spec is None or spec.loader is None:
            raise ImportError(
                f"Failed to load RMBG module spec for {file_path}"
            )

        module = importlib.util.module_from_spec(spec)
        sys.modules[full_name] = module
        try:
            spec.loader.exec_module(module)
        except ModuleNotFoundError as exc:
            raise ImportError(
                "Missing optional dependency required by RMBG-2.0 model "
                "code. Install the project's Hugging Face vision extras "
                "such as kornia and timm."
            ) from exc
        return module

    @staticmethod
    def _pick_device() -> str:
        """Return a safe torch device string for RMBG inference."""
        if not torch.cuda.is_available():
            return "cpu"

        try:
            torch.cuda.current_device()
            _ = torch.zeros(1, device="cuda:0")
            return "cuda:0"
        except Exception:
            logging.getLogger(__name__).warning(
                "CUDA reported available but is unusable; falling back to "
                "CPU",
                exc_info=True,
            )
            return "cpu"

    def remove_background(self, image: Image.Image) -> Image.Image:
        """Return an RGBA image with the predicted alpha mask applied."""
        if image is None:
            raise ValueError("No image provided")

        self._load()
        image_rgb = image.convert("RGB")
        transform = transforms.Compose(
            [
                transforms.Resize((1024, 1024)),
                transforms.ToTensor(),
                transforms.Normalize(
                    [0.485, 0.456, 0.406],
                    [0.229, 0.224, 0.225],
                ),
            ]
        )
        input_tensor = transform(image_rgb).unsqueeze(0).to(self._device)

        with torch.no_grad():
            predictions = self._model(input_tensor)[-1].sigmoid().detach().cpu()

        mask = transforms.ToPILImage()(predictions[0].squeeze())
        output = image.convert("RGBA")
        output.putalpha(mask.resize(image.size))
        return output

    def remove_background_to_png_bytes(self, image: Image.Image) -> bytes:
        """Return the background-removed image encoded as PNG bytes."""
        binary = convert_image_to_binary(self.remove_background(image))
        if binary is None:
            raise RuntimeError("Failed to convert output image to PNG bytes")
        return binary