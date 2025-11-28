"""FLUX GGUF conversion mixin.

This mixin handles automatic conversion of safetensors FLUX models to GGUF format
for more efficient loading without VRAM spikes.

NOTE: GGUF conversion for diffusion models is complex and requires specific handling.
This mixin primarily checks for existing GGUF files and helps locate them.
For creating new GGUF files, users should use external tools like:
- llama.cpp's convert scripts
- Pre-converted GGUF models from CivitAI or Hugging Face
"""

import gc
import os
from pathlib import Path
from typing import Optional, List
import numpy as np

import torch

try:
    import gguf
    from gguf import GGUFWriter, GGMLQuantizationType
    HAS_GGUF = True
except ImportError:
    HAS_GGUF = False
    GGUFWriter = None
    GGMLQuantizationType = None

from safetensors.torch import load_file

from airunner.enums import SignalCode


class FluxGGUFConversionMixin:
    """Handles conversion of safetensors models to GGUF format."""

    # Default quantization type for GGUF conversion
    GGUF_QUANT_TYPE = "Q8_0" if HAS_GGUF else None  # Q8_0 is more compatible
    
    def _get_gguf_path(self, model_path: str) -> Path:
        """Get the GGUF file path for a given model path.
        
        The GGUF file is stored alongside the original model with .gguf extension.
        """
        model_path = Path(model_path)
        if model_path.suffix.lower() == ".safetensors":
            return model_path.with_suffix(".gguf")
        return model_path.parent / f"{model_path.stem}.gguf"
    
    def _find_existing_gguf(self, model_path: str) -> Optional[Path]:
        """Find existing GGUF files in the model directory.
        
        Looks for .gguf files that might be usable.
        """
        model_path = Path(model_path)
        model_dir = model_path.parent if model_path.is_file() else model_path
        
        # Look for GGUF files in the directory
        gguf_files = list(model_dir.glob("*.gguf"))
        
        # Prefer files with matching stem or containing 'flux' or 'transformer'
        for gguf_file in gguf_files:
            stem_lower = gguf_file.stem.lower()
            if model_path.stem.lower() in stem_lower:
                return gguf_file
            if "flux" in stem_lower or "transformer" in stem_lower:
                return gguf_file
        
        # Return first gguf file if any exist
        if gguf_files:
            return gguf_files[0]
        
        return None
    
    def _gguf_exists(self, model_path: str) -> bool:
        """Check if a GGUF version of the model exists."""
        gguf_path = self._get_gguf_path(model_path)
        if gguf_path.exists():
            # Verify it's a valid size (not a failed conversion)
            if gguf_path.stat().st_size > 1024 * 1024:  # At least 1MB
                return True
        
        # Also check for any existing GGUF in directory
        existing = self._find_existing_gguf(model_path)
        return existing is not None
    
    def _should_use_gguf(self, model_path: str) -> bool:
        """Determine if we should use GGUF for this model.
        
        Returns True if:
        - GGUF library is available
        - Model is already GGUF, OR a valid pre-converted GGUF version exists
        
        NOTE: Automatic safetensors->GGUF conversion is disabled because
        diffusers requires a specific GGUF format. For GGUF models, download
        pre-converted versions from HuggingFace (e.g., city96/FLUX.1-dev-gguf).
        """
        if not HAS_GGUF:
            self.logger.debug("GGUF library not available")
            return False
        
        model_path = Path(model_path)
        
        # Already a GGUF file
        if model_path.suffix.lower() == ".gguf":
            return True
        
        # Check for existing pre-converted GGUF
        if self._gguf_exists(model_path):
            return True
        
        # NOTE: We do NOT automatically convert safetensors to GGUF
        # because diffusers requires a specific GGUF format that our
        # manual conversion doesn't produce correctly.
        
        return False
    
    def _get_or_create_gguf(self, model_path: str) -> Optional[Path]:
        """Get existing GGUF file or attempt to create one from safetensors.
        
        Returns the path to the GGUF file, or None if not available.
        """
        model_path = Path(model_path)
        
        # Already a GGUF file
        if model_path.suffix.lower() == ".gguf":
            return model_path
        
        # Check exact path first
        gguf_path = self._get_gguf_path(str(model_path))
        if gguf_path.exists() and gguf_path.stat().st_size > 1024 * 1024:
            self.logger.info(f"Using existing GGUF file: {gguf_path}")
            return gguf_path
        
        # Check for any existing GGUF in directory
        existing = self._find_existing_gguf(str(model_path))
        if existing:
            self.logger.info(f"Found existing GGUF file: {existing}")
            return existing
        
        # Not a safetensors file we can convert
        if model_path.suffix.lower() != ".safetensors":
            return None
        
        # Try to convert
        self.logger.info(f"Converting {model_path.name} to GGUF format...")
        self.emit_signal(
            SignalCode.UPDATE_DOWNLOAD_LOG,
            {"message": f"Converting {model_path.name} to GGUF (one-time, ~2-5 min)..."},
        )
        
        try:
            self._convert_safetensors_to_gguf(model_path, gguf_path)
            
            # Verify the output
            if gguf_path.exists() and gguf_path.stat().st_size > 1024 * 1024:
                self.logger.info(f"✓ Created GGUF file: {gguf_path}")
                self.emit_signal(
                    SignalCode.UPDATE_DOWNLOAD_LOG,
                    {"message": f"✓ GGUF conversion complete."},
                )
                return gguf_path
            else:
                self.logger.warning("GGUF file too small, conversion may have failed")
                if gguf_path.exists():
                    gguf_path.unlink()
                return None
                
        except Exception as e:
            self.logger.warning(f"GGUF conversion failed: {e}. Falling back to BitsAndBytes.")
            # Clean up failed file
            if gguf_path.exists():
                try:
                    gguf_path.unlink()
                except:
                    pass
            return None
    
    def _convert_safetensors_to_gguf(
        self, 
        input_path: Path, 
        output_path: Path,
        quant_type: str = None
    ) -> None:
        """Convert a safetensors transformer model to GGUF format.
        
        Uses Q8_0 quantization which is most compatible with the gguf library.
        
        Args:
            input_path: Path to the safetensors file
            output_path: Path for the output GGUF file
            quant_type: Quantization type (default: Q8_0)
        """
        if not HAS_GGUF:
            raise RuntimeError("GGUF library not installed")
        
        quant_type = quant_type or self.GGUF_QUANT_TYPE
        
        self.logger.info(f"Loading safetensors weights from {input_path}...")
        
        # Load the safetensors file
        state_dict = load_file(str(input_path))
        
        self.logger.info(f"Converting {len(state_dict)} tensors to GGUF ({quant_type})...")
        
        # Create GGUF writer
        writer = GGUFWriter(str(output_path), "flux")
        
        # Add metadata
        writer.add_name(input_path.stem)
        writer.add_description(f"FLUX transformer converted from {input_path.name}")
        
        # Convert and add tensors
        tensors_converted = 0
        tensors_failed = 0
        total_tensors = len(state_dict)
        
        for name, tensor in state_dict.items():
            try:
                # Convert to float32 numpy array (required for gguf quantization)
                if tensor.dtype == torch.bfloat16:
                    tensor = tensor.to(torch.float32)
                elif tensor.dtype == torch.float16:
                    tensor = tensor.to(torch.float32)
                
                np_tensor = tensor.cpu().numpy().astype(np.float32)
                
                # Determine quantization based on tensor shape and size
                n_dims = len(np_tensor.shape)
                
                # Small tensors (biases, norms, 1D) stay as F32
                if n_dims <= 1 or np_tensor.size < 256:
                    writer.add_tensor(name, np_tensor, raw_dtype=GGMLQuantizationType.F32)
                    tensors_converted += 1
                else:
                    # Try to quantize larger tensors
                    try:
                        # Q8_0 requires specific alignment - reshape if needed
                        # Q8_0 block size is 32 elements
                        if np_tensor.shape[-1] % 32 == 0:
                            quantized = gguf.quantize(np_tensor, GGMLQuantizationType.Q8_0)
                            writer.add_tensor(name, quantized, raw_dtype=GGMLQuantizationType.Q8_0)
                        else:
                            # Keep as F16 for incompatible shapes
                            np_f16 = tensor.cpu().to(torch.float16).numpy()
                            writer.add_tensor(name, np_f16, raw_dtype=GGMLQuantizationType.F16)
                        tensors_converted += 1
                    except Exception as qe:
                        # Fall back to F16 on quantization error
                        self.logger.debug(f"Quantization failed for {name}: {qe}, using F16")
                        np_f16 = tensor.cpu().to(torch.float16).numpy()
                        writer.add_tensor(name, np_f16, raw_dtype=GGMLQuantizationType.F16)
                        tensors_converted += 1
                
                # Log progress every 50 tensors
                if tensors_converted % 50 == 0:
                    progress = (tensors_converted / total_tensors) * 100
                    self.logger.info(f"Conversion progress: {progress:.1f}% ({tensors_converted}/{total_tensors})")
                    
            except Exception as e:
                self.logger.warning(f"Failed to convert tensor {name}: {e}")
                tensors_failed += 1
        
        if tensors_converted == 0:
            raise RuntimeError("No tensors were converted successfully")
        
        # Write the file
        self.logger.info(f"Writing GGUF file ({tensors_converted} tensors, {tensors_failed} failed)...")
        writer.write_header_to_file()
        writer.write_kv_data_to_file()
        writer.write_tensors_to_file()
        writer.close()
        
        # Clean up
        del state_dict
        gc.collect()
        
        # Verify output
        if output_path.exists():
            output_size_gb = output_path.stat().st_size / (1024**3)
            self.logger.info(
                f"✓ GGUF conversion complete: {tensors_converted}/{total_tensors} tensors, "
                f"{output_size_gb:.2f} GB"
            )
        else:
            raise RuntimeError("GGUF file was not created")
    
    def _cleanup_gguf_cache(self, model_path: str) -> None:
        """Remove GGUF cache for a model."""
        gguf_path = self._get_gguf_path(model_path)
        if gguf_path.exists():
            self.logger.info(f"Removing GGUF cache: {gguf_path}")
            gguf_path.unlink()
