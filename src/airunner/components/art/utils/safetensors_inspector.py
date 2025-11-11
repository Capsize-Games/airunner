"""Utility to inspect SafeTensors files and detect included components."""

from pathlib import Path
from typing import Dict
from safetensors import safe_open


class SafeTensorsInspector:
    """Inspect SafeTensors files to detect which model components are included."""

    @staticmethod
    def inspect_file(file_path: str) -> Dict[str, bool]:
        """Inspect a SafeTensors file and detect included components.

        Args:
            file_path: Path to the .safetensors file

        Returns:
            Dict with keys: has_transformer, has_text_encoder, has_text_encoder_2, has_vae
        """
        file_path = Path(file_path)

        if not file_path.exists() or not str(file_path).endswith(
            ".safetensors"
        ):
            return {
                "has_transformer": False,
                "has_text_encoder": False,
                "has_text_encoder_2": False,
                "has_vae": False,
                "error": "File not found or not a SafeTensors file",
            }

        try:
            # Open SafeTensors file and read tensor keys
            with safe_open(str(file_path), framework="pt", device="cpu") as f:
                keys = set(f.keys())

            # Detect components based on key prefixes
            has_transformer = any(
                k.startswith(
                    ("transformer.", "model.diffusion_model.", "unet.")
                )
                for k in keys
            )

            has_text_encoder = any(
                k.startswith(
                    (
                        "text_encoder.",
                        "cond_stage_model.",
                        "conditioner.embedders.0",
                    )
                )
                for k in keys
            )

            has_text_encoder_2 = any(
                k.startswith(("text_encoder_2.", "conditioner.embedders.1"))
                for k in keys
            )

            has_vae = any(
                k.startswith(("vae.", "first_stage_model.", "autoencoder."))
                for k in keys
            )

            return {
                "has_transformer": has_transformer,
                "has_text_encoder": has_text_encoder,
                "has_text_encoder_2": has_text_encoder_2,
                "has_vae": has_vae,
                "total_keys": len(keys),
            }

        except Exception as e:
            return {
                "has_transformer": False,
                "has_text_encoder": False,
                "has_text_encoder_2": False,
                "has_vae": False,
                "error": str(e),
            }

    @staticmethod
    def get_file_type(file_path: str) -> str:
        """Determine the type of SafeTensors file.

        Args:
            file_path: Path to the .safetensors file

        Returns:
            One of: 'full', 'unet_only', 'with_t5_fp16', 'with_t5_fp8', 'unknown'
        """
        info = SafeTensorsInspector.inspect_file(file_path)

        if "error" in info:
            return "unknown"

        has_transformer = info["has_transformer"]
        has_text_encoder = info["has_text_encoder"]
        has_text_encoder_2 = info["has_text_encoder_2"]
        has_vae = info["has_vae"]

        # UNet/Transformer only (recommended for quantization)
        if (
            has_transformer
            and not has_text_encoder
            and not has_text_encoder_2
            and not has_vae
        ):
            return "unet_only"

        # Full model with all components
        if (
            has_transformer
            and has_text_encoder
            and has_text_encoder_2
            and has_vae
        ):
            return "full"

        # Transformer + text encoders (common distribution format)
        if has_transformer and (has_text_encoder or has_text_encoder_2):
            # Check file size to guess if T5 is fp16 or fp8
            file_size_gb = Path(file_path).stat().st_size / (1024**3)
            if file_size_gb > 18:
                return "with_t5_fp16"
            elif file_size_gb > 14:
                return "with_t5_fp8"
            else:
                return "with_encoders"

        return "unknown"

    @staticmethod
    def should_download_text_encoders(file_path: str) -> bool:
        """Check if we need to download separate text encoder files.

        Args:
            file_path: Path to the .safetensors file

        Returns:
            True if separate text encoder files are needed
        """
        info = SafeTensorsInspector.inspect_file(file_path)

        if "error" in info:
            return True  # Assume we need them if we can't inspect

        # Need separate files if either encoder is missing
        return not info["has_text_encoder"] or not info["has_text_encoder_2"]

    @staticmethod
    def should_download_vae(file_path: str) -> bool:
        """Check if we need to download separate VAE file.

        Args:
            file_path: Path to the .safetensors file

        Returns:
            True if separate VAE file is needed
        """
        info = SafeTensorsInspector.inspect_file(file_path)

        if "error" in info:
            return True  # Assume we need it if we can't inspect

        return not info["has_vae"]
