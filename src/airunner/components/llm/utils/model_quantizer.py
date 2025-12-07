"""
Model quantization utilities.

NOTE: This project uses bitsandbytes for runtime quantization (2/4/8-bit).
Quantization happens automatically at model load time via transformers' BitsAndBytesConfig.

This GPTQModel-based quantizer is DEPRECATED and non-functional due to installation issues.
Use the bitsandbytes integration in llm_model_manager.py instead.

See:
- src/airunner/components/llm/managers/llm_model_manager.py (_get_quantization_config)
- src/airunner/components/application/workers/model_quantization_worker.py
"""

import logging
from pathlib import Path
from typing import Optional, Literal, Callable

from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger


class ModelQuantizer:
    """
    Quantize LLM models using GPTQModel for optimal inference performance.

    Supports:
    - 4-bit quantization (recommended for function calling)
    - 2-bit quantization (for maximum compression, may reduce quality)
    - Calibration dataset selection
    - Progress callbacks for GUI integration
    """

    def __init__(self):
        """Initialize quantizer."""
        self.logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)

    def quantize_model(
        self,
        model_path: str,
        output_path: str,
        bits: Literal[2, 4] = 4,
        group_size: int = 128,
        desc_act: bool = True,
        use_triton: bool = False,
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ) -> Path:
        """
        Quantize a model using GPTQModel.

        Args:
            model_path: Path to unquantized model
            output_path: Path to save quantized model
            bits: Quantization bits (2 or 4, default: 4)
            group_size: Group size for quantization (default: 128)
            desc_act: Use descending activation order (default: True)
            use_triton: Use Triton kernels (faster but requires specific GPU)
            progress_callback: Optional callback(stage_name, progress_percent)

        Returns:
            Path to quantized model
        """
        try:
            from gptqmodel import GPTQModel, QuantizeConfig
            from transformers import AutoTokenizer
        except ImportError as e:
            error_msg = (
                "GPTQModel not installed or PyTorch missing.\n\n"
                "SETUP REQUIRED:\n"
                "1. Install PyTorch first:\n"
                "   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121\n\n"
                "2. Then install GPTQModel:\n"
                "   pip install gptqmodel\n\n"
                "See docs/QUANTIZATION_SETUP.md for detailed instructions.\n\n"
                f"Original error: {str(e)}"
            )
            raise ImportError(error_msg)

        self.logger.info(
            f"Quantizing model from {model_path} to {bits}-bit..."
        )

        if progress_callback:
            progress_callback("Loading model", 0.0)

        # Load tokenizer
        tokenizer = AutoTokenizer.from_pretrained(model_path, use_fast=True)

        # Create quantization config
        quantize_config = QuantizeConfig(
            bits=bits,
            group_size=group_size,
            desc_act=desc_act,
            damp_percent=0.01,
        )

        if progress_callback:
            progress_callback("Loading unquantized model", 0.1)

        # Load model
        model = GPTQModel.from_pretrained(
            model_path,
            quantize_config=quantize_config,
            trust_remote_code=False,
        )

        if progress_callback:
            progress_callback("Preparing calibration data", 0.3)

        # Prepare calibration data (use a small dataset for speed)
        # For function calling models, use diverse prompts
        calibration_data = self._get_calibration_data(tokenizer)

        if progress_callback:
            progress_callback("Quantizing", 0.4)

        # Quantize the model
        model.quantize(calibration_data)

        if progress_callback:
            progress_callback("Saving quantized model", 0.9)

        # Save quantized model
        output_dir = Path(output_path)
        output_dir.mkdir(parents=True, exist_ok=True)

        model.save_quantized(output_dir, use_safetensors=True)
        tokenizer.save_pretrained(output_dir)

        # Copy essential files from original model
        self._copy_essential_files(model_path, output_path)

        if progress_callback:
            progress_callback("Complete", 1.0)

        self.logger.info(f"Quantized model saved to: {output_path}")
        return output_dir

    def _get_calibration_data(self, tokenizer, num_samples: int = 128):
        """
        Get calibration data for quantization.

        Uses a diverse set of prompts including:
        - General knowledge questions
        - Code generation
        - Function calling examples
        - Multilingual content
        """
        # Sample prompts covering different use cases
        prompts = [
            "What is the capital of France?",
            "Write a Python function to calculate factorial.",
            "Explain quantum computing in simple terms.",
            "How do I make a chocolate cake?",
            "What are the benefits of exercise?",
            "Write a haiku about technology.",
            "Explain the theory of relativity.",
            "How does photosynthesis work?",
            "What is machine learning?",
            "Write a short story about a robot.",
            # Function calling prompts
            "Generate an image of a sunset over the ocean.",
            "Search for information about climate change.",
            "Create a calendar event for tomorrow at 3 PM.",
            "Send an email to john@example.com about the meeting.",
            "Calculate the square root of 144.",
            # Multilingual
            "¿Cuál es la capital de España?",
            "Qu'est-ce que l'intelligence artificielle?",
            "Was ist Quantencomputer?",
            # Code
            "def bubble_sort(arr):",
            "class Calculator:",
            "import numpy as np",
            # Math
            "Solve: 2x + 5 = 15",
            "What is the derivative of x^2?",
        ]

        # Repeat prompts to reach num_samples
        while len(prompts) < num_samples:
            prompts.extend(
                prompts[: min(len(prompts), num_samples - len(prompts))]
            )

        # Tokenize
        calibration_data = []
        for prompt in prompts[:num_samples]:
            tokens = tokenizer(
                prompt,
                return_tensors="pt",
                max_length=512,
                truncation=True,
            )
            calibration_data.append(tokens)

        return calibration_data

    def _copy_essential_files(self, source_dir: str, dest_dir: str):
        """Copy essential files that aren't handled by GPTQModel save."""
        import shutil

        essential_files = [
            "tekken.json",  # Mistral V3-Tekken tokenizer
            "params.json",  # Mistral-specific config
            "generation_config.json",
            "special_tokens_map.json",
        ]

        source_path = Path(source_dir)
        dest_path = Path(dest_dir)

        for filename in essential_files:
            source_file = source_path / filename
            if source_file.exists():
                dest_file = dest_path / filename
                if not dest_file.exists():
                    shutil.copy2(source_file, dest_file)
                    self.logger.info(f"Copied {filename}")

    def estimate_quantized_size(
        self, model_path: str, bits: Literal[2, 4]
    ) -> dict:
        """
        Estimate the size of the quantized model.

        Args:
            model_path: Path to unquantized model
            bits: Quantization bits

        Returns:
            Dict with size estimates in GB
        """
        try:
            import json

            config_path = Path(model_path) / "config.json"
            if not config_path.exists():
                raise FileNotFoundError(f"Config not found: {config_path}")

            with open(config_path) as f:
                config = json.load(f)

            # Get parameter count
            # Common architectures store this differently
            num_params = None
            if "num_parameters" in config:
                num_params = config["num_parameters"]
            else:
                # Estimate from architecture
                hidden_size = config.get("hidden_size", 4096)
                num_layers = config.get("num_hidden_layers", 32)
                vocab_size = config.get("vocab_size", 32000)

                # Rough estimate: embeddings + layers
                num_params = vocab_size * hidden_size  # Embeddings
                num_params += (
                    num_layers * (hidden_size**2) * 12
                )  # Layers (rough)

            # Calculate sizes
            # Full precision: 4 bytes per parameter (float32)
            # Half precision: 2 bytes (float16)
            # Quantized: bits/8 bytes per parameter
            full_size_gb = (num_params * 4) / (1024**3)
            half_size_gb = (num_params * 2) / (1024**3)
            quant_size_gb = (num_params * bits / 8) / (1024**3)

            return {
                "parameters": num_params,
                "full_precision_gb": round(full_size_gb, 2),
                "half_precision_gb": round(half_size_gb, 2),
                f"{bits}bit_quantized_gb": round(quant_size_gb, 2),
                "compression_ratio": round(full_size_gb / quant_size_gb, 2),
            }

        except Exception as e:
            self.logger.error(f"Failed to estimate size: {e}")
            return {}


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    quantizer = ModelQuantizer()

    # Example: Quantize Ministral-3-8B to 4-bit
    model_path = "/path/to/ministral3-8b"
    output_path = "/path/to/ministral3-8b-4bit-gptq"

    def progress(stage, percent):
        print(f"{stage}: {percent * 100:.1f}%")

    quantizer.quantize_model(
        model_path=model_path,
        output_path=output_path,
        bits=4,
        progress_callback=progress,
    )

    # Estimate size
    size_info = quantizer.estimate_quantized_size(model_path, bits=4)
    print("Size estimates:", size_info)
