#!/usr/bin/env python3
"""Test script to verify Ministral 3 BF16 model loading with 4-bit quantization.

Run this after the BF16 model download completes:
    python src/airunner/components/llm/tests/test_ministral3_loading.py

Expected flow:
1. Patch config files (if needed)
2. Load config and tokenizer
3. Load model with BitsAndBytes 4-bit quantization
4. Test generation
5. Save quantized model to disk
6. Reload quantized model to verify save worked
"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))

os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

import torch
from transformers import AutoConfig, AutoTokenizer, BitsAndBytesConfig

# Import Mistral3 specific model
try:
    from transformers import Mistral3ForConditionalGeneration
except ImportError:
    print("ERROR: Mistral3ForConditionalGeneration not available in transformers")
    print("Please upgrade transformers: pip install -U transformers")
    sys.exit(1)

from airunner.components.llm.utils.ministral3_config_patcher import (
    needs_patching,
    patch_ministral3_config,
    is_ministral3_model,
)


def main():
    model_path = os.path.expanduser(
        "~/.local/share/airunner/text/models/llm/causallm/Ministral-3-8B-Instruct-2512-BF16"
    )
    quantized_path = os.path.join(os.path.dirname(model_path), "Ministral-3-8B-Instruct-2512-BF16-4bit")

    print("=" * 60)
    print("Ministral 3 BF16 Model Loading Test")
    print("=" * 60)

    # Step 1: Check if model exists
    print(f"\n1. Checking model path: {model_path}")
    if not os.path.exists(model_path):
        print("ERROR: Model not found! Please download first:")
        print("  huggingface-cli download mistralai/Ministral-3-8B-Instruct-2512-BF16")
        sys.exit(1)

    # Count safetensor files
    safetensor_files = [f for f in os.listdir(model_path) if f.endswith(".safetensors")]
    if len(safetensor_files) < 4:
        print(f"ERROR: Only found {len(safetensor_files)} safetensor files")
        print("Expected 4 sharded safetensor files. Download may be incomplete.")
        sys.exit(1)
    print(f"   Found {len(safetensor_files)} safetensor files ✓")

    # Step 2: Check and patch config
    print(f"\n2. Checking if config patching needed...")
    print(f"   Is Ministral 3 model: {is_ministral3_model(model_path)}")
    if needs_patching(model_path):
        print("   Patching config files...")
        if patch_ministral3_config(model_path):
            print("   Config patched successfully ✓")
        else:
            print("ERROR: Failed to patch config!")
            sys.exit(1)
    else:
        print("   Config already patched ✓")

    # Step 3: Load config
    print("\n3. Loading config...")
    config = AutoConfig.from_pretrained(model_path, trust_remote_code=True)
    print(f"   Model type: {config.model_type} ✓")
    print(f"   Architecture: {config.architectures} ✓")

    # Step 4: Load tokenizer
    print("\n4. Loading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(
        model_path,
        trust_remote_code=True,
        fix_mistral_regex=True,
    )
    print(f"   Vocab size: {tokenizer.vocab_size} ✓")

    # Step 5: Load model with 4-bit quantization
    print("\n5. Loading model with BitsAndBytes 4-bit quantization...")
    print("   This may take a few minutes...")

    quantization_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=torch.bfloat16,
    )

    model = Mistral3ForConditionalGeneration.from_pretrained(
        model_path,
        quantization_config=quantization_config,
        device_map="auto",
        trust_remote_code=True,
        torch_dtype=torch.bfloat16,
    )
    print(f"   Model loaded ✓")
    print(f"   Device: {model.device}")

    # Step 6: Test generation
    print("\n6. Testing text generation...")
    messages = [{"role": "user", "content": "Hello! What is 2 + 2?"}]
    text = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    inputs = tokenizer(text, return_tensors="pt").to(model.device)

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=50,
            do_sample=True,
            temperature=0.7,
            pad_token_id=tokenizer.pad_token_id,
        )

    response = tokenizer.decode(
        outputs[0][inputs.input_ids.shape[1] :], skip_special_tokens=True
    )
    print(f"   Response: {response[:100]}..." if len(response) > 100 else f"   Response: {response}")
    print("   Generation successful ✓")

    # Step 7: Save quantized model
    print(f"\n7. Saving quantized model to: {quantized_path}")
    os.makedirs(quantized_path, exist_ok=True)
    model.save_pretrained(quantized_path, safe_serialization=True)

    # Copy tokenizer files (but NOT config.json - save_pretrained already saved it with quantization_config)
    import shutil
    for f in ["tokenizer.json", "tokenizer_config.json", "tekken.json", "special_tokens_map.json"]:
        src = os.path.join(model_path, f)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(quantized_path, f))
    print("   Quantized model saved ✓")

    # Step 8: Verify reload works
    print("\n8. Verifying quantized model can be reloaded...")
    del model
    torch.cuda.empty_cache()

    # The saved config.json now has quantization_config, so transformers will
    # automatically recognize it's a BitsAndBytes quantized model
    model_reloaded = Mistral3ForConditionalGeneration.from_pretrained(
        quantized_path,
        device_map="auto",
        trust_remote_code=True,
    )
    print("   Quantized model reloaded ✓")

    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED!")
    print("=" * 60)
    print(f"\nQuantized model saved to: {quantized_path}")
    print("This model will load much faster on subsequent runs.")


if __name__ == "__main__":
    main()
