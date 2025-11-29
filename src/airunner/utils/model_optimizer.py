"""Model optimization utility for converting models to efficient formats.

This module provides intelligent model format management:
- GGUF file discovery and preference
- SafeTensors → GGUF conversion for LLMs (requires llama.cpp tools)
- Automatic format detection based on settings

IMPORTANT: BitsAndBytes quantized safetensors CANNOT be converted to GGUF.
GGUF conversion requires original FP16/FP32 weights.

For GGUF support, users have two options:
1. Download pre-quantized GGUF from HuggingFace (automatic via UI)
2. Convert original (non-quantized) safetensors using llama.cpp tools

GGUF Conversion Requirements (for option 2):
    1. Clone llama.cpp:
       git clone https://github.com/ggerganov/llama.cpp ~/llama.cpp
    
    2. Build the quantize tool:
       cd ~/llama.cpp && make quantize
    
    3. Install Python dependencies:
       pip install -r ~/llama.cpp/requirements.txt
    
    4. Convert and quantize:
       python ~/llama.cpp/convert_hf_to_gguf.py /path/to/model --outtype f16
       ~/llama.cpp/llama-quantize model-f16.gguf model-Q4_K_M.gguf Q4_K_M
"""

import os
import subprocess
import shutil
from pathlib import Path
from typing import Optional, Tuple, Literal, List
from enum import Enum

from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger


class ModelFormat(Enum):
    """Supported model formats."""
    SAFETENSORS = "safetensors"
    GGUF = "gguf"
    ONNX = "onnx"
    PYTORCH = "pytorch"


class QuantizationType(Enum):
    """GGUF quantization types ordered by size/quality tradeoff."""
    Q2_K = "Q2_K"      # Smallest, lowest quality
    Q3_K_M = "Q3_K_M"  # Small
    Q4_K_M = "Q4_K_M"  # Balanced (recommended)
    Q5_K_M = "Q5_K_M"  # Good quality
    Q6_K = "Q6_K"      # High quality
    Q8_0 = "Q8_0"      # Highest quality, largest
    F16 = "F16"        # Full precision


class ModelOptimizer:
    """Utility for converting models to optimal formats.
    
    This class handles:
    - Detection of existing model formats
    - Conversion between formats (SafeTensors → GGUF, SafeTensors → ONNX)
    - Caching of converted models to avoid re-conversion
    - Automatic selection of quantization based on settings
    
    Usage:
        optimizer = ModelOptimizer()
        
        # Convert LLM to GGUF if needed
        gguf_path = optimizer.ensure_gguf(
            model_path="/path/to/llm",
            quantization="Q4_K_M"
        )
        
        # Convert embedding model to ONNX if needed
        onnx_path = optimizer.ensure_onnx(
            model_path="/path/to/embedding"
        )
    """
    
    def __init__(self):
        self.logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)
        self._llama_cpp_path: Optional[str] = None
    
    def detect_format(self, model_path: str) -> ModelFormat:
        """Detect the format of a model at the given path.
        
        Args:
            model_path: Path to model directory or file
            
        Returns:
            Detected ModelFormat
        """
        path = Path(model_path)
        
        if path.is_file():
            suffix = path.suffix.lower()
            if suffix == ".gguf":
                return ModelFormat.GGUF
            elif suffix == ".onnx":
                return ModelFormat.ONNX
            elif suffix == ".safetensors":
                return ModelFormat.SAFETENSORS
            elif suffix in (".bin", ".pt", ".pth"):
                return ModelFormat.PYTORCH
        
        if path.is_dir():
            # Check for GGUF files
            gguf_files = list(path.glob("*.gguf"))
            if gguf_files:
                return ModelFormat.GGUF
            
            # Check for ONNX files
            onnx_files = list(path.glob("*.onnx")) + list(path.glob("**/*.onnx"))
            if onnx_files:
                return ModelFormat.ONNX
            
            # Check for SafeTensors
            safetensor_files = list(path.glob("*.safetensors"))
            if safetensor_files:
                return ModelFormat.SAFETENSORS
            
            # Check for PyTorch
            pytorch_files = list(path.glob("*.bin")) + list(path.glob("pytorch_model*.bin"))
            if pytorch_files:
                return ModelFormat.PYTORCH
        
        # Default to safetensors if we can't determine
        return ModelFormat.SAFETENSORS
    
    def get_gguf_path(self, model_path: str, quantization: str = "Q4_K_M") -> str:
        """Get the expected path for a GGUF version of a model.
        
        Args:
            model_path: Original model path
            quantization: Quantization type (e.g., Q4_K_M)
            
        Returns:
            Path where GGUF file would be stored
        """
        path = Path(model_path)
        model_name = path.name if path.is_dir() else path.stem
        gguf_filename = f"{model_name}-{quantization}.gguf"
        return str(path.parent / model_name / gguf_filename) if path.is_dir() else str(path.parent / gguf_filename)
    
    def find_existing_gguf(self, model_path: str) -> Optional[str]:
        """Find an existing GGUF file for a model.
        
        Args:
            model_path: Path to model directory
            
        Returns:
            Path to GGUF file if found, None otherwise
        """
        path = Path(model_path)
        
        if path.is_file() and path.suffix.lower() == ".gguf":
            return str(path)
        
        if path.is_dir():
            # Look for GGUF files in the directory
            gguf_files = list(path.glob("*.gguf"))
            if gguf_files:
                # Prefer Q4_K_M if available
                for f in gguf_files:
                    if "Q4_K_M" in f.name or "q4_k_m" in f.name:
                        return str(f)
                # Return first found
                return str(gguf_files[0])
        
        return None
    
    def has_llama_cpp_convert(self) -> bool:
        """Check if llama.cpp conversion tools are available.
        
        Returns:
            True if conversion is possible
        """
        # Check for llama-cpp-python's bundled convert script
        try:
            import llama_cpp
            llama_path = Path(llama_cpp.__file__).parent
            convert_script = llama_path / "llama_cpp" / "convert.py"
            if convert_script.exists():
                self._llama_cpp_path = str(convert_script)
                return True
        except ImportError:
            pass
        
        # Check for standalone llama.cpp convert script
        # Common locations
        for path in [
            Path.home() / "llama.cpp" / "convert_hf_to_gguf.py",
            Path("/usr/local/bin/convert_hf_to_gguf.py"),
            Path.home() / ".local" / "bin" / "convert_hf_to_gguf.py",
        ]:
            if path.exists():
                self._llama_cpp_path = str(path)
                return True
        
        # Check if convert script is in PATH
        if shutil.which("convert_hf_to_gguf.py"):
            self._llama_cpp_path = "convert_hf_to_gguf.py"
            return True
        
        return False
    
    def convert_to_gguf(
        self,
        model_path: str,
        quantization: str = "Q4_K_M",
        output_path: Optional[str] = None,
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """Convert a HuggingFace model to GGUF format.
        
        Args:
            model_path: Path to HuggingFace model directory
            quantization: Quantization type (Q2_K, Q3_K_M, Q4_K_M, Q5_K_M, Q6_K, Q8_0, F16)
            output_path: Optional output path for GGUF file
            
        Returns:
            Tuple of (success, gguf_path, error_message)
        """
        path = Path(model_path)
        
        if not path.exists():
            return False, None, f"Model path does not exist: {model_path}"
        
        # Check for existing GGUF
        existing = self.find_existing_gguf(model_path)
        if existing:
            self.logger.info(f"Found existing GGUF: {existing}")
            return True, existing, None
        
        # Determine output path
        if output_path is None:
            model_name = path.name if path.is_dir() else path.stem
            output_path = str(path / f"{model_name}-{quantization}.gguf")
        
        # Check if conversion tools are available
        if not self.has_llama_cpp_convert():
            return False, None, (
                "GGUF conversion requires llama.cpp tools. "
                "Install with: pip install llama-cpp-python or clone llama.cpp"
            )
        
        try:
            self.logger.info(f"Converting {model_path} to GGUF ({quantization})...")
            
            # Build conversion command
            cmd = [
                "python", self._llama_cpp_path,
                str(path),
                "--outfile", output_path,
                "--outtype", self._quantization_to_outtype(quantization),
            ]
            
            # Run conversion
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600,  # 1 hour timeout
            )
            
            if result.returncode != 0:
                return False, None, f"Conversion failed: {result.stderr}"
            
            if not Path(output_path).exists():
                return False, None, "Conversion completed but output file not found"
            
            self.logger.info(f"Successfully converted to GGUF: {output_path}")
            return True, output_path, None
            
        except subprocess.TimeoutExpired:
            return False, None, "Conversion timed out after 1 hour"
        except Exception as e:
            return False, None, f"Conversion error: {str(e)}"
    
    def _quantization_to_outtype(self, quantization: str) -> str:
        """Convert quantization name to llama.cpp outtype.
        
        Args:
            quantization: Our quantization name
            
        Returns:
            llama.cpp outtype string
        """
        mapping = {
            "Q2_K": "q2_k",
            "Q3_K_M": "q3_k_m",
            "Q4_K_M": "q4_k_m",
            "Q5_K_M": "q5_k_m",
            "Q6_K": "q6_k",
            "Q8_0": "q8_0",
            "F16": "f16",
        }
        return mapping.get(quantization, "q4_k_m")
    
    def ensure_gguf(
        self,
        model_path: str,
        quantization: str = "Q4_K_M",
    ) -> Optional[str]:
        """Ensure a GGUF version of the model exists.
        
        If a GGUF file already exists, returns its path.
        Otherwise, attempts conversion from SafeTensors.
        
        Args:
            model_path: Path to model directory
            quantization: Desired quantization type
            
        Returns:
            Path to GGUF file, or None if not available
        """
        # Check for existing GGUF
        existing = self.find_existing_gguf(model_path)
        if existing:
            return existing
        
        # Try to convert
        success, gguf_path, error = self.convert_to_gguf(model_path, quantization)
        if success:
            return gguf_path
        
        self.logger.warning(f"Could not create GGUF: {error}")
        return None
    
    def get_optimal_format(
        self,
        model_type: Literal["llm", "embedding", "vision"],
        quantization_bits: int = 4,
    ) -> ModelFormat:
        """Determine optimal format based on model type and settings.
        
        Args:
            model_type: Type of model (llm, embedding, vision)
            quantization_bits: Quantization setting (0 = GGUF, 2/4/8 = BnB)
            
        Returns:
            Recommended ModelFormat
        """
        if model_type == "llm":
            # GGUF is preferred for LLMs when quantization_bits is 0
            if quantization_bits == 0:
                return ModelFormat.GGUF
            # Otherwise use SafeTensors with BitsAndBytes
            return ModelFormat.SAFETENSORS
        
        elif model_type == "embedding":
            # ONNX can be faster for embeddings but SafeTensors is more compatible
            return ModelFormat.SAFETENSORS
        
        elif model_type == "vision":
            # Vision models typically use SafeTensors
            return ModelFormat.SAFETENSORS
        
        return ModelFormat.SAFETENSORS
    
    def bits_to_gguf_quantization(self, quantization_bits: int) -> str:
        """Map quantization bits setting to GGUF quantization type.
        
        Args:
            quantization_bits: User setting (0, 2, 4, 8)
            
        Returns:
            GGUF quantization type string
        """
        mapping = {
            0: "Q4_K_M",  # Default for "GGUF" selection
            2: "Q2_K",
            4: "Q4_K_M",
            8: "Q8_0",
        }
        return mapping.get(quantization_bits, "Q4_K_M")


# Global instance for convenience
_optimizer: Optional[ModelOptimizer] = None


def get_model_optimizer() -> ModelOptimizer:
    """Get the global ModelOptimizer instance.
    
    Returns:
        ModelOptimizer singleton
    """
    global _optimizer
    if _optimizer is None:
        _optimizer = ModelOptimizer()
    return _optimizer
