from __future__ import annotations
import torch
from safetensors.torch import load_file
from torchvision import transforms
import importlib.machinery
import importlib.util
import logging
import os
import sys
from dataclasses import dataclass
from typing import Optional

from PIL import Image

from airunner.settings import MODELS_DIR
from airunner.utils.image.convert_image_to_binary import convert_image_to_binary


@dataclass(frozen=True)
class RMBGModelSpec:
    repo_id: str = "briaai/RMBG-2.0"
    model_dir_name: str = "RMBG-2.0"

    @property
    def local_dir(self) -> str:
        return os.path.join(MODELS_DIR, "vision", "models", "rmbg", self.model_dir_name)


class RMBGModelManager:
    """Loads and runs BRIA RMBG-2.0 background removal.

    Loads strictly from the on-disk model directory managed by our custom
    downloader and avoids Hugging Face dynamic module caching.
    """

    def __init__(self, spec: Optional[RMBGModelSpec] = None):
        self.spec = spec or RMBGModelSpec()
        self._model = None
        self._device = None

    def required_files(self) -> list[str]:
        # Kept in sync with bootstrap data for briaai/RMBG-2.0
        return [
            "config.json",
            "model.safetensors",
            "preprocessor_config.json",
            "BiRefNet_config.py",
            "birefnet.py",
        ]

    def missing_files(self) -> list[str]:
        missing: list[str] = []
        base = self.spec.local_dir
        for rel in self.required_files():
            if not os.path.exists(os.path.join(base, rel)):
                missing.append(rel)
        return missing

    def is_available_on_disk(self) -> bool:
        return len(self.missing_files()) == 0

    def _load(self):
        if self._model is not None:
            return

        self._device = self._pick_device(torch)

        base_dir = self.spec.local_dir
        config_py = os.path.join(base_dir, "BiRefNet_config.py")
        model_py = os.path.join(base_dir, "birefnet.py")
        weights_path = os.path.join(base_dir, "model.safetensors")

        if not (os.path.exists(config_py) and os.path.exists(model_py) and os.path.exists(weights_path)):
            missing = [
                p
                for p in ("BiRefNet_config.py", "birefnet.py", "model.safetensors")
                if not os.path.exists(os.path.join(base_dir, p))
            ]
            raise FileNotFoundError(f"Missing RMBG model files on disk: {missing}")

        # Avoid `transformers` dynamic module cache (which writes to
        # ~/.cache/huggingface/modules) by loading the repo's python files
        # directly from our on-disk model directory.
        package_name = f"airunner_rmbg2_{abs(hash(base_dir))}"

        if package_name not in sys.modules:
            pkg = importlib.util.module_from_spec(
                importlib.machinery.ModuleSpec(package_name, loader=None, is_package=True)
            )
            pkg.__path__ = [base_dir]  # type: ignore[attr-defined]
            sys.modules[package_name] = pkg

        def _load_submodule(module_name: str, file_path: str):
            full_name = f"{package_name}.{module_name}"
            if full_name in sys.modules:
                return sys.modules[full_name]

            spec = importlib.util.spec_from_file_location(full_name, file_path)
            if spec is None or spec.loader is None:
                raise ImportError(f"Failed to load RMBG module spec for {file_path}")

            module = importlib.util.module_from_spec(spec)
            sys.modules[full_name] = module
            try:
                spec.loader.exec_module(module)
            except ModuleNotFoundError as e:
                raise ImportError(
                    "Missing optional dependency required by RMBG-2.0 model code. "
                    "Install the project's Hugging Face/vision extras (e.g. `kornia`, `timm`)."
                ) from e
            return module

        config_mod = _load_submodule("BiRefNet_config", config_py)
        model_mod = _load_submodule("birefnet", model_py)

        if not hasattr(config_mod, "BiRefNetConfig"):
            raise ImportError("RMBG config module does not define BiRefNetConfig")
        if not hasattr(model_mod, "BiRefNet"):
            raise ImportError("RMBG model module does not define BiRefNet")

        BiRefNetConfig = getattr(config_mod, "BiRefNetConfig")
        BiRefNet = getattr(model_mod, "BiRefNet")

        config = BiRefNetConfig(bb_pretrained=False)
        # Load on CPU first; some environments (and/or safetensors builds) do
        # not support loading tensors directly onto CUDA.
        model = BiRefNet(config=config)

        state_dict = load_file(weights_path, device="cpu")
        model.load_state_dict(state_dict, strict=False)

        model = model.to(self._device)

        self._model = model.eval()

    def _pick_device(self, torch) -> str:
        """Return a safe torch device string.

        Some environments report CUDA available but still fail at runtime
        (e.g. driver/runtime mismatch). In that case, fall back to CPU.
        """

        if not torch.cuda.is_available():
            return "cpu"

        try:
            torch.cuda.current_device()
            _ = torch.zeros(1, device="cuda:0")
            return "cuda:0"
        except Exception:
            logging.getLogger(__name__).warning(
                "CUDA reported available but is unusable; falling back to CPU",
                exc_info=True,
            )
            return "cpu"

    def remove_background(self, image: Image.Image) -> Image.Image:
        """Return an RGBA image with RMBG alpha matte applied."""

        if image is None:
            raise ValueError("No image provided")

        self._load()

        image_rgb = image.convert("RGB")

        transform_image = transforms.Compose(
            [
                transforms.Resize((1024, 1024)),
                transforms.ToTensor(),
                transforms.Normalize(
                    [0.485, 0.456, 0.406],
                    [0.229, 0.224, 0.225],
                ),
            ]
        )

        input_tensor = transform_image(image_rgb).unsqueeze(0).to(self._device)

        with torch.no_grad():
            preds = self._model(input_tensor)[-1].sigmoid().detach().cpu()

        pred = preds[0].squeeze()
        pred_pil = transforms.ToPILImage()(pred)
        mask = pred_pil.resize(image.size)

        out = image.convert("RGBA")
        out.putalpha(mask)
        return out

    def remove_background_to_png_bytes(self, image: Image.Image) -> bytes:
        out = self.remove_background(image)
        binary = convert_image_to_binary(out)
        if binary is None:
            raise RuntimeError("Failed to convert output image to PNG bytes")
        return binary
