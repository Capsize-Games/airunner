"""Model loading functionality for LLM models.

This mixin handles:
- GPU memory logging and management
- Mistral3 model detection
- Model configuration preparation
- Quantization application
- Model loading from pretrained weights
- Pre-quantized model loading
- Runtime quantization
"""

import traceback
from typing import Any, Dict, Optional, TYPE_CHECKING

import torch
from transformers import (
    AutoConfig,
    AutoModel,
    AutoModelForCausalLM,
    BitsAndBytesConfig,
)

from airunner.settings import AIRUNNER_LOCAL_FILES_ONLY
from airunner.utils.memory.clear_memory import clear_memory
from airunner.utils.memory.gpu_memory_stats import gpu_memory_stats
from airunner.components.llm.utils.ministral3_config_patcher import (
    needs_patching,
    patch_ministral3_config,
)
from airunner.components.llm.config.provider_config import LLMProviderConfig

if TYPE_CHECKING:
    pass

# Optional import for Mistral3 support
try:
    from transformers import Mistral3ForConditionalGeneration
except ImportError:
    Mistral3ForConditionalGeneration = None


class ModelLoaderMixin:
    """Mixin for LLM model loading functionality."""

    def _log_gpu_memory_status(self) -> None:
        """Log current GPU memory usage.

        Uses utility functions to clear memory and get GPU stats.
        """
        if not torch.cuda.is_available():
            return

        clear_memory(device=0)
        stats = gpu_memory_stats(torch.device("cuda:0"))
        self.logger.info(
            f"GPU memory before loading: {stats['free']:.2f}GB free / "
            f"{stats['total']:.2f}GB total"
        )

    def _detect_mistral3_model(self, config: AutoConfig) -> bool:
        """Check if model configuration indicates Mistral3 architecture.

        Args:
            config: Model configuration from AutoConfig

        Returns:
            True if Mistral3 model, False otherwise
        """
        is_mistral3_type = (
            hasattr(config, "model_type") and config.model_type == "mistral3"
        )
        is_mistral3_arch = hasattr(config, "architectures") and any(
            "Mistral3" in arch for arch in (config.architectures or [])
        )
        return is_mistral3_type or is_mistral3_arch

    def _get_model_info_for_context(self) -> Dict[str, Any]:
        """Lookup model metadata used for context sizing.

        Returns:
            Model info dict from provider config if available.
        """
        model_id = getattr(self.llm_generator_settings, "model_id", None)
        if model_id:
            try:
                return LLMProviderConfig.get_model_info("local", model_id)
            except Exception:
                return {}
        return {}

    def _apply_context_settings(self, config: AutoConfig) -> Dict[str, Any]:
        """Apply target context and YaRN rope scaling to a config.

        Updates internal tracking fields `_native_context_length`,
        `_target_context_length`, and `_using_yarn` for downstream
        tokenizer/model setup.
        """
        model_info = self._get_model_info_for_context()
        native_ctx = model_info.get("native_context_length") or model_info.get(
            "context_length"
        )
        if native_ctx is None:
            native_ctx = getattr(config, "max_position_embeddings", None)

        yarn_max_ctx = model_info.get("yarn_max_context_length")
        supports_yarn = model_info.get("supports_yarn", False)
        target_ctx = native_ctx

        use_yarn_setting = getattr(self.llm_settings, "use_yarn", False)
        should_scale = (
            bool(use_yarn_setting)
            and bool(supports_yarn)
            and yarn_max_ctx
            and native_ctx
            and yarn_max_ctx > native_ctx
        )

        if should_scale:
            target_ctx = yarn_max_ctx
            factor = float(target_ctx) / float(native_ctx)
            config.rope_scaling = {
                "type": "yarn",
                "factor": factor,
                "original_max_position_embeddings": native_ctx,
            }
            self.logger.info(
                f"Applying YaRN scaling: native={native_ctx}, target={target_ctx}, factor={factor:.2f}"
            )

        if target_ctx:
            if hasattr(config, "max_position_embeddings"):
                config.max_position_embeddings = target_ctx
            if hasattr(config, "max_sequence_length"):
                config.max_sequence_length = target_ctx

        self._native_context_length = native_ctx
        self._target_context_length = target_ctx
        self._using_yarn = bool(should_scale)

        return {
            "native_context_length": native_ctx,
            "target_context_length": target_ctx,
            "use_yarn": bool(should_scale),
        }

    def _prepare_base_model_kwargs(self, is_mistral3: bool) -> Dict[str, Any]:
        """Prepare base kwargs for model loading.

        Args:
            is_mistral3: Whether loading a Mistral3 model

        Returns:
            Dictionary with base model loading parameters
        """
        model_kwargs = {
            "local_files_only": AIRUNNER_LOCAL_FILES_ONLY,
            "trust_remote_code": True,
            "attn_implementation": self.attn_implementation,
        }

        if not is_mistral3:
            model_kwargs["use_cache"] = self.use_cache

        return model_kwargs

    def _apply_quantization_to_kwargs(
        self,
        model_kwargs: Dict[str, Any],
        quantization_config: Optional[BitsAndBytesConfig],
        dtype: str,
    ) -> None:
        """Apply quantization configuration to model kwargs.

        Modifies model_kwargs in-place to add quantization settings.

        Args:
            model_kwargs: Model loading kwargs to modify
            quantization_config: BitsAndBytes config or None for full precision
            dtype: Quantization dtype string
        """
        if quantization_config is None:
            self._apply_full_precision_kwargs(model_kwargs)
            return

        self._apply_quantized_kwargs(model_kwargs, quantization_config, dtype)

    def _apply_full_precision_kwargs(
        self, model_kwargs: Dict[str, Any]
    ) -> None:
        """Apply full precision model loading kwargs.

        Args:
            model_kwargs: Model loading kwargs to modify
        """
        model_kwargs["torch_dtype"] = self.torch_dtype
        model_kwargs["device_map"] = self.device
        self.logger.warning(
            "No quantization config - loading in full precision!"
        )

    def _apply_quantized_kwargs(
        self,
        model_kwargs: Dict[str, Any],
        quantization_config: BitsAndBytesConfig,
        dtype: str,
    ) -> None:
        """Apply quantized model loading kwargs.

        Args:
            model_kwargs: Model loading kwargs to modify
            quantization_config: BitsAndBytes configuration
            dtype: Quantization dtype string
        """
        model_kwargs["quantization_config"] = quantization_config
        model_kwargs["device_map"] = "auto"
        model_kwargs["dtype"] = self.torch_dtype

        max_memory = self._configure_quantization_memory(dtype)
        if max_memory:
            model_kwargs["max_memory"] = max_memory

    def _load_model_from_pretrained(
        self,
        model_path: str,
        is_mistral3: bool,
        model_kwargs: Dict[str, Any],
        config: Optional[AutoConfig] = None,
    ) -> None:
        """Load model from pretrained weights.

        Args:
            model_path: Path to model directory
            is_mistral3: Whether to use Mistral3 loader
            model_kwargs: Model loading parameters
        """
        if is_mistral3:
            self._load_mistral3_model(model_path, model_kwargs, config)
        else:
            self._load_standard_model(model_path, model_kwargs, config)

    def _load_mistral3_model(
        self, model_path: str, model_kwargs: Dict[str, Any], config: Optional[AutoConfig]
    ) -> None:
        """Load Mistral3 model.

        Args:
            model_path: Path to model directory
            model_kwargs: Model loading parameters

        Raises:
            ImportError: If Mistral3ForConditionalGeneration not available
        """
        self.logger.info(
            "Loading Mistral3 model with Mistral3ForConditionalGeneration"
        )
        if Mistral3ForConditionalGeneration is None:
            raise ImportError(
                "Mistral3ForConditionalGeneration not available. "
                "Ensure transformers supports Mistral3 models."
            )
        self._model = Mistral3ForConditionalGeneration.from_pretrained(
            model_path, config=config, **model_kwargs
        )
        self.logger.info("✓ Mistral3 model loaded successfully")

    def _load_standard_model(
        self, model_path: str, model_kwargs: Dict[str, Any], config: Optional[AutoConfig]
    ) -> None:
        """Load standard causal LM model with fallback.

        Falls back to AutoModel if architecture not recognized by
        AutoModelForCausalLM.

        Args:
            model_path: Path to model directory
            model_kwargs: Model loading parameters
        """
        try:
            self._model = AutoModelForCausalLM.from_pretrained(
                model_path, config=config, **model_kwargs
            )
        except ValueError as ve:
            if "Unrecognized configuration class" in str(ve):
                self._handle_unrecognized_architecture(
                    model_path, model_kwargs, ve
                )
            else:
                raise

    def _handle_unrecognized_architecture(
        self, model_path: str, model_kwargs: Dict[str, Any], error: ValueError
    ) -> None:
        """Handle unrecognized model architecture.

        Args:
            model_path: Path to model directory
            model_kwargs: Model loading parameters
            error: Original ValueError from AutoModelForCausalLM
        """
        self.logger.warning(
            f"AutoModelForCausalLM doesn't recognize model architecture: "
            f"{type(error).__name__}"
        )
        self.logger.info(
            "Falling back to AutoModel.from_pretrained() for custom architecture"
        )
        self._model = AutoModel.from_pretrained(model_path, **model_kwargs)

    def _load_model(self) -> None:
        """Load the LLM model with appropriate quantization.

        Main entry point for model loading. Handles:
        - Pre-quantized model detection
        - Runtime quantization
        - Adapter loading
        - Error handling
        """
        if self._model is not None:
            return

        self._log_gpu_memory_status()

        try:
            self._execute_model_loading()
        except Exception as e:
            self._handle_model_loading_error(e)

    def _execute_model_loading(self) -> None:
        """Execute the model loading process.

        Determines whether to use pre-quantized model or runtime quantization.
        """
        dtype = self._select_dtype()
        quantized_path = self._get_quantized_model_path(self.model_path, dtype)

        if self._should_use_pre_quantized(dtype, quantized_path):
            self.logger.info(
                f"✓ Found existing {dtype} quantized model at {quantized_path}"
            )
            self._load_pre_quantized_model(quantized_path, dtype)
        else:
            self._load_with_runtime_or_full_precision(dtype)

        self._load_adapters()

    def _should_use_pre_quantized(
        self, dtype: str, quantized_path: str
    ) -> bool:
        """Check if should use pre-quantized model.

        Args:
            dtype: Quantization dtype
            quantized_path: Path to pre-quantized model

        Returns:
            True if pre-quantized model should be used
        """
        return dtype in [
            "4bit",
            "8bit",
        ] and self._check_quantized_model_exists(quantized_path)

    def _load_with_runtime_or_full_precision(self, dtype: str) -> None:
        """Load with runtime quantization or full precision.

        Args:
            dtype: Quantization dtype
        """
        if dtype in ["4bit", "8bit"]:
            self.logger.info(
                f"No pre-quantized {dtype} model found - "
                "will quantize at runtime and save"
            )
        self._load_with_runtime_quantization(dtype)

    def _handle_model_loading_error(self, error: Exception) -> None:
        """Handle errors during model loading.

        Args:
            error: Exception that occurred
        """
        self.logger.error(
            f"Error loading model: {type(error).__name__}: {str(error)}"
        )
        self.logger.error(f"Model traceback:\n{traceback.format_exc()}")
        self._model = None

    def _load_pre_quantized_model(
        self, quantized_path: str, dtype: str
    ) -> None:
        """Load a pre-saved BitsAndBytes quantized model from disk.

        The saved config.json already contains the quantization_config,
        so transformers will automatically recognize it's quantized.
        We must NOT pass a quantization_config here, as that would try
        to re-quantize already-quantized weights (causing uint8 error).

        Args:
            quantized_path: Path to pre-quantized model
            dtype: Quantization dtype used
        """
        self.logger.info(
            f"Loading pre-saved {dtype} quantized model from {quantized_path}"
        )

        config = self._load_quantized_model_config(quantized_path)
        is_mistral3 = self._detect_mistral3_model(config)
        model_kwargs = self._prepare_pre_quantized_kwargs(is_mistral3)

        self._load_model_from_pretrained(
            quantized_path, is_mistral3, model_kwargs, config
        )

        self.logger.info(
            f"✓ Pre-quantized {dtype} model loaded successfully from disk"
        )

    def _load_quantized_model_config(self, quantized_path: str) -> AutoConfig:
        """Load configuration for pre-quantized model.

        Args:
            quantized_path: Path to pre-quantized model

        Returns:
            Model configuration
        """
        # Patch Ministral 3 config files if needed (fixes transformers compatibility issues)
        self._patch_ministral3_if_needed(quantized_path)

        config = AutoConfig.from_pretrained(
            quantized_path,
            local_files_only=AIRUNNER_LOCAL_FILES_ONLY,
            trust_remote_code=True,
        )
        self._apply_context_settings(config)
        return config

    def _prepare_pre_quantized_kwargs(
        self, is_mistral3: bool
    ) -> Dict[str, Any]:
        """Prepare kwargs for loading pre-quantized model.

        Args:
            is_mistral3: Whether loading Mistral3 model

        Returns:
            Model loading kwargs without quantization_config
        """
        model_kwargs = self._prepare_base_model_kwargs(is_mistral3)
        # Don't pass quantization_config - it's already in saved config.json
        model_kwargs["device_map"] = "auto"
        model_kwargs["torch_dtype"] = self.torch_dtype
        # Do NOT set max_memory for pre-quantized models - let transformers handle it
        # The quantization config in config.json already specifies memory requirements
        return model_kwargs

    def _load_with_runtime_quantization(self, dtype: str) -> None:
        """Load model with runtime BitsAndBytes quantization.

        Args:
            dtype: Quantization dtype to use
        """
        quantization_config = self._create_bitsandbytes_config(dtype)

        config = self._load_model_config_for_runtime_quantization()
        is_mistral3 = self._detect_mistral3_model(config)
        model_kwargs = self._prepare_runtime_quantization_kwargs(
            is_mistral3, quantization_config, dtype
        )

        self._load_model_from_pretrained(
            self.model_path, is_mistral3, model_kwargs, config
        )

        self._save_quantized_if_applicable(dtype, quantization_config)

    def _load_model_config_for_runtime_quantization(self) -> AutoConfig:
        """Load model configuration for runtime quantization.

        Returns:
            Model configuration
        """
        # Patch Ministral 3 config files if needed (fixes transformers compatibility issues)
        self._patch_ministral3_if_needed(self.model_path)

        config = AutoConfig.from_pretrained(
            self.model_path,
            local_files_only=AIRUNNER_LOCAL_FILES_ONLY,
            trust_remote_code=True,
        )
        self._apply_context_settings(config)
        return config

    def _patch_ministral3_if_needed(self, model_path: str) -> None:
        """Patch Ministral 3 config files if needed for transformers compatibility.

        Ministral 3 models have config bugs that prevent loading:
        - config.json: text_config.model_type "ministral3" -> "mistral"
        - tokenizer_config.json: tokenizer_class and extra_special_tokens fixes

        Args:
            model_path: Path to model directory
        """
        if needs_patching(model_path):
            self.logger.info(
                f"Patching Ministral 3 config files for transformers compatibility: {model_path}"
            )
            if patch_ministral3_config(model_path):
                self.logger.info("✓ Ministral 3 config patched successfully")
            else:
                self.logger.warning(
                    "⚠ Failed to patch Ministral 3 config - loading may fail"
                )

    def _prepare_runtime_quantization_kwargs(
        self,
        is_mistral3: bool,
        quantization_config: Optional[BitsAndBytesConfig],
        dtype: str,
    ) -> Dict[str, Any]:
        """Prepare kwargs for runtime quantization.

        Args:
            is_mistral3: Whether loading Mistral3 model
            quantization_config: Quantization configuration
            dtype: Quantization dtype

        Returns:
            Model loading kwargs with quantization settings
        """
        model_kwargs = self._prepare_base_model_kwargs(is_mistral3)
        self._apply_quantization_to_kwargs(
            model_kwargs, quantization_config, dtype
        )
        return model_kwargs

    def _save_quantized_if_applicable(
        self, dtype: str, quantization_config: Optional[BitsAndBytesConfig]
    ) -> None:
        """Save quantized model if applicable.

        Args:
            dtype: Quantization dtype used
            quantization_config: Quantization configuration used
        """
        if dtype not in ["4bit", "8bit"]:
            return

        try:
            self.logger.info(
                f"Saving {dtype} quantized model for faster future loads..."
            )
            self._save_loaded_model_quantized(
                self.model_path, dtype, quantization_config
            )
        except Exception as e:
            self.logger.warning(
                f"Could not save quantized model: {e}. "
                "Will use runtime quantization on next load."
            )
