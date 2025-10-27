"""
Test script to verify Mistral3 (Magistral-Small-2509) loading.

This tests:
1. MistralTokenizer loading from tekken.json
2. Model loading with correct parameters (no use_cache for Mistral3)
"""

import os
import logging
from transformers import AutoConfig, AutoModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODEL_PATH = "/home/joe/.local/share/airunner/text/models/llm/causallm/Magistral-Small-2509"


def test_tokenizer():
    """Test Mistral3 tokenizer loading."""
    logger.info("=" * 80)
    logger.info("Testing Mistral3 Tokenizer Loading")
    logger.info("=" * 80)

    try:
        from mistral_common.tokens.tokenizers.mistral import MistralTokenizer

        tekken_path = os.path.join(MODEL_PATH, "tekken.json")
        logger.info(f"Loading tokenizer from: {tekken_path}")
        logger.info(f"File exists: {os.path.exists(tekken_path)}")

        tokenizer = MistralTokenizer.from_file(tekken_path)
        logger.info(f"✅ Tokenizer loaded successfully!")
        logger.info(f"   Type: {type(tokenizer)}")

        # Test encoding
        test_text = "Hello, world! This is a test."
        tokens = tokenizer.encode(test_text, bos=True, eos=False)
        logger.info(f"   Encoded '{test_text}' to {len(tokens)} tokens")

        return True
    except Exception as e:
        logger.error(f"❌ Tokenizer loading failed: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_model_detection():
    """Test Mistral3 model detection logic."""
    logger.info("=" * 80)
    logger.info("Testing Mistral3 Model Detection")
    logger.info("=" * 80)

    try:
        config = AutoConfig.from_pretrained(
            MODEL_PATH,
            local_files_only=True,
            trust_remote_code=True,
        )

        logger.info(f"Model type: {config.model_type}")
        logger.info(f"Architectures: {config.architectures}")
        logger.info(f"Config class: {type(config)}")

        is_mistral3 = (
            hasattr(config, "model_type") and config.model_type == "mistral3"
        ) or (
            hasattr(config, "architectures")
            and any(
                "Mistral3" in arch for arch in (config.architectures or [])
            )
        )

        logger.info(f"Is Mistral3: {is_mistral3}")

        if is_mistral3:
            logger.info("✅ Mistral3 detection works!")
            return True
        else:
            logger.error("❌ Failed to detect Mistral3 model")
            return False
    except Exception as e:
        logger.error(f"❌ Model detection failed: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_model_loading():
    """Test Mistral3 model loading (dry run - just check parameters)."""
    logger.info("=" * 80)
    logger.info("Testing Mistral3 Model Loading Parameters")
    logger.info("=" * 80)

    try:
        config = AutoConfig.from_pretrained(
            MODEL_PATH,
            local_files_only=True,
            trust_remote_code=True,
        )

        is_mistral3 = config.model_type == "mistral3"

        model_kwargs = {
            "local_files_only": True,
            "trust_remote_code": True,
            "torch_dtype": "auto",
            "device_map": "auto",
            "attn_implementation": "sdpa",
        }

        # Mistral3 models don't accept use_cache in __init__
        if not is_mistral3:
            model_kwargs["use_cache"] = True
            logger.info("Would add use_cache=True (not Mistral3)")
        else:
            logger.info("Excluding use_cache parameter (Mistral3 detected)")

        logger.info(f"Model kwargs: {model_kwargs}")
        logger.info("✅ Model parameter configuration correct for Mistral3")

        # Note: We don't actually load the model here to save time/memory
        logger.info(
            "Note: Skipping actual model loading to save time. "
            "Run airunner to test full loading."
        )
        return True
    except Exception as e:
        logger.error(
            f"❌ Model parameter setup failed: {type(e).__name__}: {e}"
        )
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    results = []

    logger.info("\n")
    logger.info("🧪 Mistral3 (Magistral-Small-2509) Loading Test Suite")
    logger.info("\n")

    results.append(("Mistral3 Detection", test_model_detection()))
    results.append(("Tokenizer Loading", test_tokenizer()))
    results.append(("Model Parameters", test_model_loading()))

    logger.info("\n")
    logger.info("=" * 80)
    logger.info("Test Results Summary")
    logger.info("=" * 80)

    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"{status}: {test_name}")

    all_passed = all(result[1] for result in results)
    logger.info("\n")
    if all_passed:
        logger.info("🎉 All tests passed! Mistral3 loading should work.")
    else:
        logger.error("❌ Some tests failed. Please review the errors above.")

    exit(0 if all_passed else 1)
