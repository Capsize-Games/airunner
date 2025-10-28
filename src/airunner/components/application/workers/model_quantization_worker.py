"""Qt worker for model quantization using bitsandbytes (runtime quantization)."""

import time
from pathlib import Path
from queue import Queue
from PySide6.QtCore import QObject, Signal

from airunner.enums import SignalCode
from airunner.utils.application.mediator_mixin import MediatorMixin


class ModelQuantizationWorker(MediatorMixin, QObject):
    """
    Worker class for model quantization status tracking.

    Note: With bitsandbytes, quantization happens at model load time,
    not as a separate preprocessing step. This worker is used to:
    1. Verify model is ready for quantized loading
    2. Update quantization config in settings
    3. Provide user feedback
    """

    progress = Signal(str, float)  # (stage, progress_0_to_1)
    finished = Signal(dict)  # config_dict
    failed = Signal(Exception)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.queue = Queue()
        self.running = False
        self.is_cancelled = False

    def add_to_queue(self, data: dict):
        """
        Add a quantization task to the queue.

        Args:
            data: Dict with keys:
                - model_path: str (path to downloaded model)
                - bits: int (4 or 8)
                - quant_type: str ("nf4" or "fp4" for 4-bit, "int8" for 8-bit)
        """
        self.queue.put(data)

    def cancel(self):
        """Cancel the current process."""
        self.is_cancelled = True
        self.running = False

    def process(self):
        """Process the quantization queue."""
        self.running = True
        while self.running and not self.is_cancelled:
            if self.queue.empty():
                time.sleep(0.1)
                continue

            try:
                task_data = self.queue.get()
                self._prepare_quantization(task_data)
            except Exception as e:
                self.failed.emit(e)
                self.emit_signal(
                    SignalCode.UPDATE_DOWNLOAD_LOG,
                    {"message": f"Quantization setup failed: {str(e)}"},
                )
            finally:
                self.running = False

    def _prepare_quantization(self, task_data: dict):
        """
        Prepare model for quantized loading.

        Since bitsandbytes does quantization at load time,
        this just verifies the model and creates the config.
        """
        model_path = task_data["model_path"]
        bits = task_data.get("bits", 4)
        quant_type = task_data.get("quant_type", "nf4")

        self.emit_signal(SignalCode.CLEAR_DOWNLOAD_STATUS_BAR)
        self.emit_signal(
            SignalCode.SET_DOWNLOAD_STATUS_LABEL,
            {"message": f"Preparing {bits}-bit quantization"},
        )

        # Stage 1: Verify model files
        self.progress.emit("Verifying model files", 0.2)
        self.emit_signal(
            SignalCode.UPDATE_DOWNLOAD_LOG,
            {"message": f"Verifying model at {model_path}"},
        )

        model_path_obj = Path(model_path)
        if not model_path_obj.exists():
            raise FileNotFoundError(f"Model not found: {model_path}")

        # Check for required files
        config_file = model_path_obj / "config.json"
        if not config_file.exists():
            raise FileNotFoundError(f"config.json not found in {model_path}")

        safetensors = list(model_path_obj.glob("*.safetensors"))
        if not safetensors:
            raise FileNotFoundError(
                f"No safetensors files found in {model_path}"
            )

        # Stage 2: Create quantization config
        self.progress.emit("Creating quantization config", 0.5)

        if bits == 4:
            from transformers import BitsAndBytesConfig

            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type=quant_type,  # "nf4" or "fp4"
                bnb_4bit_use_double_quant=True,  # Nested quantization for more memory savings
                bnb_4bit_compute_dtype="bfloat16",  # Compute dtype for 4-bit base models
            )
            config_dict = {
                "load_in_4bit": True,
                "bnb_4bit_quant_type": quant_type,
                "bnb_4bit_use_double_quant": True,
                "bnb_4bit_compute_dtype": "bfloat16",
            }
        elif bits == 8:
            from transformers import BitsAndBytesConfig

            bnb_config = BitsAndBytesConfig(
                load_in_8bit=True,
            )
            config_dict = {
                "load_in_8bit": True,
            }
        else:
            raise ValueError(f"Unsupported bits: {bits}. Use 4 or 8.")

        # Stage 3: Estimate VRAM usage
        self.progress.emit("Estimating VRAM requirements", 0.8)

        # Get model size from config
        try:
            import json

            with open(config_file) as f:
                config = json.load(f)

            # Estimate based on common model sizes
            vocab_size = config.get("vocab_size", 0)
            hidden_size = config.get("hidden_size", 0)
            num_hidden_layers = config.get("num_hidden_layers", 0)

            # Rough VRAM estimate formula:
            # (vocab_size * hidden_size + num_layers * hidden_size * hidden_size) * bytes_per_param
            #
            # This approximates:
            # - Embedding layer: vocab_size * hidden_size parameters
            # - Transformer layers: num_layers * (hidden_size * hidden_size) parameters
            #
            # Note: This is a simplified estimate that doesn't account for attention heads,
            # intermediate layers, or activation memory. Actual VRAM usage may be higher.
            #
            # Reference: https://huggingface.co/docs/transformers/main/en/model_memory_anatomy
            bytes_per_param = (
                0.5 if bits == 4 else 1
            )  # 4-bit = 0.5 bytes, 8-bit = 1 byte
            params = (
                vocab_size * hidden_size
                + num_hidden_layers * hidden_size * hidden_size
            )
            estimated_vram_gb = (params * bytes_per_param) / (1024**3)

            config_dict["estimated_vram_gb"] = round(estimated_vram_gb, 2)

        except Exception as e:
            self.emit_signal(
                SignalCode.UPDATE_DOWNLOAD_LOG,
                {"message": f"Could not estimate VRAM: {e}"},
            )
            config_dict["estimated_vram_gb"] = "unknown"

        # Complete
        self.progress.emit("Complete", 1.0)
        config_dict["model_path"] = str(model_path)
        config_dict["bits"] = bits
        config_dict["quant_type"] = quant_type if bits == 4 else "int8"

        self.emit_signal(
            SignalCode.UPDATE_DOWNLOAD_LOG,
            {
                "message": f"✓ Model ready for {bits}-bit quantization (est. {config_dict.get('estimated_vram_gb', '?')} GB VRAM)"
            },
        )

        self.finished.emit(config_dict)
