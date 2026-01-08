"""Utility to patch Ministral 3 model config files for transformers compatibility.

Mistral AI's Ministral 3 models have several config issues that prevent them from
loading with HuggingFace transformers:

1. config.json: text_config.model_type is "ministral3" but transformers only has
   "mistral" registered in CONFIG_MAPPING. We change it to "mistral".

2. tokenizer_config.json: tokenizer_class is "TokenizersBackend" which doesn't
   exist in transformers. We change it to "PreTrainedTokenizerFast".

3. tokenizer_config.json: extra_special_tokens is a list but transformers expects
   a dict (or None). We remove it.

This patcher should be called after downloading a Ministral 3 model and before
attempting to load it with transformers.
"""

import json
import logging
import os
from pathlib import Path
from typing import Union

logger = logging.getLogger(__name__)


def patch_ministral3_config(model_path: Union[str, Path]) -> bool:
    """Patch Ministral 3 config files for transformers compatibility.

    Args:
        model_path: Path to the downloaded model directory

    Returns:
        True if patching was successful or not needed, False on error
    """
    model_path = Path(model_path)

    if not model_path.exists():
        logger.warning(f"Model path does not exist: {model_path}")
        return False

    success = True

    # Patch config.json
    config_path = model_path / "config.json"
    if config_path.exists():
        if not _patch_config_json(config_path):
            success = False

    # Patch tokenizer_config.json
    tokenizer_config_path = model_path / "tokenizer_config.json"
    if tokenizer_config_path.exists():
        if not _patch_tokenizer_config_json(tokenizer_config_path):
            success = False

    return success


def _patch_config_json(config_path: Path) -> bool:
    """Patch config.json to fix text_config.model_type.

    Args:
        config_path: Path to config.json

    Returns:
        True if successful, False on error
    """
    try:
        with open(config_path, "r") as f:
            config = json.load(f)

        modified = False

        # Fix text_config.model_type: "ministral3" -> "mistral"
        if "text_config" in config:
            text_config = config["text_config"]
            if text_config.get("model_type") == "ministral3":
                text_config["model_type"] = "mistral"
                modified = True
                logger.info(
                    f"Patched config.json: text_config.model_type 'ministral3' -> 'mistral'"
                )

        # Remove quantization_config if it contains FP8 settings
        # (prevents conflicts with BitsAndBytes quantization)
        if "quantization_config" in config:
            quant_config = config["quantization_config"]
            if quant_config.get("quant_method") == "fp8":
                del config["quantization_config"]
                modified = True
                logger.info(
                    "Patched config.json: removed FP8 quantization_config"
                )

        if modified:
            with open(config_path, "w") as f:
                json.dump(config, f, indent=2)
            logger.info(f"Saved patched config.json: {config_path}")

        return True

    except Exception as e:
        logger.error(f"Failed to patch config.json: {e}")
        return False


def _patch_tokenizer_config_json(tokenizer_config_path: Path) -> bool:
    """Patch tokenizer_config.json to fix tokenizer_class and extra_special_tokens.

    Args:
        tokenizer_config_path: Path to tokenizer_config.json

    Returns:
        True if successful, False on error
    """
    try:
        with open(tokenizer_config_path, "r") as f:
            config = json.load(f)

        modified = False

        # Fix tokenizer_class: "TokenizersBackend" -> "PreTrainedTokenizerFast"
        if config.get("tokenizer_class") == "TokenizersBackend":
            config["tokenizer_class"] = "PreTrainedTokenizerFast"
            modified = True
            logger.info(
                "Patched tokenizer_config.json: tokenizer_class 'TokenizersBackend' -> 'PreTrainedTokenizerFast'"
            )

        # Remove extra_special_tokens if it's a list (should be dict or None)
        if "extra_special_tokens" in config:
            if isinstance(config["extra_special_tokens"], list):
                del config["extra_special_tokens"]
                modified = True
                logger.info(
                    "Patched tokenizer_config.json: removed invalid extra_special_tokens list"
                )

        if modified:
            with open(tokenizer_config_path, "w") as f:
                json.dump(config, f, indent=2)
            logger.info(
                f"Saved patched tokenizer_config.json: {tokenizer_config_path}"
            )

        return True

    except Exception as e:
        logger.error(f"Failed to patch tokenizer_config.json: {e}")
        return False


def is_ministral3_model(model_path: Union[str, Path]) -> bool:
    """Check if a model directory contains a Ministral 3 model.

    Args:
        model_path: Path to the model directory

    Returns:
        True if this is a Ministral 3 model
    """
    model_path = Path(model_path)
    config_path = model_path / "config.json"

    if not config_path.exists():
        return False

    try:
        with open(config_path, "r") as f:
            config = json.load(f)

        # Check model_type
        if config.get("model_type") == "mistral3":
            return True

        # Check architectures
        architectures = config.get("architectures", [])
        if any("Mistral3" in arch for arch in architectures):
            return True

        return False

    except Exception:
        return False


def needs_patching(model_path: Union[str, Path]) -> bool:
    """Check if a Ministral 3 model needs patching.

    Args:
        model_path: Path to the model directory

    Returns:
        True if patching is needed
    """
    model_path = Path(model_path)

    if not is_ministral3_model(model_path):
        return False

    # Check config.json
    config_path = model_path / "config.json"
    if config_path.exists():
        try:
            with open(config_path, "r") as f:
                config = json.load(f)

            # Check for unpatched text_config.model_type
            text_config = config.get("text_config", {})
            if text_config.get("model_type") == "ministral3":
                return True

            # Check for FP8 quantization config
            quant_config = config.get("quantization_config", {})
            if quant_config.get("quant_method") == "fp8":
                return True

        except Exception:
            pass

    # Check tokenizer_config.json
    tokenizer_config_path = model_path / "tokenizer_config.json"
    if tokenizer_config_path.exists():
        try:
            with open(tokenizer_config_path, "r") as f:
                config = json.load(f)

            # Check for TokenizersBackend
            if config.get("tokenizer_class") == "TokenizersBackend":
                return True

            # Check for list-type extra_special_tokens
            if isinstance(config.get("extra_special_tokens"), list):
                return True

        except Exception:
            pass

    return False
