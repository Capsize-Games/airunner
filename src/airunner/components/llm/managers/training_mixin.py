import os
import os
from typing import Optional, List, Tuple

from datasets import Dataset
from transformers import (
    TrainingArguments,
    Trainer,
    default_data_collator,
    TrainerCallback,
)
from peft import (
    LoraConfig,
    get_peft_model,
    PeftModel,
    prepare_model_for_kbit_training,
)

from airunner.components.llm.training_presets import (
    TrainingScenario,
    get_preset,
)


class TrainingMixin:
    """
    Thin TrainingMixin that manages LoRA PEFT adapter training.

    Responsibilities:
    - Build a simple dataset from (prompt,response) pairs
    - Create or load a LoRA adapter via PEFT
    - Run Trainer with a small callback bridge to report progress
    - Support cooperative cancellation via `cancel_fine_tune()`
    - Save only adapter artifacts (avoid saving base model)
    """

    def get_adapter_path(self, adapter_name: Optional[str] = None) -> str:
        """Get path for a specific adapter or the default adapter."""
        adapter_name = adapter_name or getattr(
            self, "_current_adapter_name", "default"
        )
        return os.path.expanduser(
            os.path.join(
                self.path_settings.base_path,
                "text",
                "models",
                "llm",
                "adapters",
                self.model_name,
                adapter_name,
            )
        )

    @property
    def peft_adapter_path(self) -> str:
        """Get current adapter path."""
        return self.get_adapter_path()

    # Backwards-compatible alias
    @property
    def adapter_path(self) -> str:
        return self.peft_adapter_path

    def train(
        self,
        training_data: List[Tuple[str, str]],
        adapter_name: str = "default",
        username: str = "User",
        botname: str = "Assistant",
        preset: Optional[TrainingScenario] = None,
        num_train_epochs: Optional[int] = None,
        learning_rate: Optional[float] = None,
        gradient_accumulation_steps: Optional[int] = None,
        per_device_train_batch_size: Optional[int] = None,
        warmup_steps: Optional[int] = None,
        logging_steps: int = 1,
        use_fp16: Optional[bool] = None,
        gradient_checkpointing: Optional[bool] = None,
        report_to: str = "none",
        optim: str = "adamw_torch",
        progress_callback: Optional[callable] = None,
    ):
        """Orchestrate training with preset or custom parameters."""
        self._validate_training_prerequisites(training_data)
        self._cancel_training = False

        # Store adapter name for path resolution
        self._current_adapter_name = adapter_name

        # Apply preset if provided, allow overrides
        params = self._resolve_training_params(
            preset=preset,
            num_train_epochs=num_train_epochs,
            learning_rate=learning_rate,
            gradient_accumulation_steps=gradient_accumulation_steps,
            per_device_train_batch_size=per_device_train_batch_size,
            warmup_steps=warmup_steps,
            use_fp16=use_fp16,
            gradient_checkpointing=gradient_checkpointing,
        )

        adapter_dir = self.get_adapter_path(adapter_name)
        os.makedirs(adapter_dir, exist_ok=True)

        tokenizer = self._ensure_tokenizer(self._tokenizer)
        ds = self._build_dataset(training_data, tokenizer, username, botname)
        model = self._prepare_peft_model(adapter_dir, preset)
        self._move_model_to_device(model)

        trainer = self._create_trainer(
            model=model,
            ds=ds,
            adapter_dir=adapter_dir,
            per_device_train_batch_size=params["per_device_train_batch_size"],
            gradient_accumulation_steps=params["gradient_accumulation_steps"],
            num_train_epochs=params["num_train_epochs"],
            learning_rate=params["learning_rate"],
            warmup_steps=params["warmup_steps"],
            logging_steps=logging_steps,
            use_fp16=params["use_fp16"],
            gradient_checkpointing=params["gradient_checkpointing"],
            report_to=report_to,
            optim=optim,
            progress_callback=progress_callback,
        )

        trainer.train()
        self._check_cancellation()
        self._finalize_training(model, adapter_dir)

    def _resolve_training_params(
        self,
        preset: Optional[TrainingScenario],
        num_train_epochs: Optional[int],
        learning_rate: Optional[float],
        gradient_accumulation_steps: Optional[int],
        per_device_train_batch_size: Optional[int],
        warmup_steps: Optional[int],
        use_fp16: Optional[bool],
        gradient_checkpointing: Optional[bool],
    ) -> dict:
        """Resolve training parameters from preset or custom values."""
        if preset:
            preset_config = get_preset(preset)
            return {
                "num_train_epochs": num_train_epochs
                or preset_config.num_train_epochs,
                "learning_rate": learning_rate or preset_config.learning_rate,
                "gradient_accumulation_steps": gradient_accumulation_steps
                or preset_config.gradient_accumulation_steps,
                "per_device_train_batch_size": per_device_train_batch_size
                or preset_config.per_device_train_batch_size,
                "warmup_steps": warmup_steps or preset_config.warmup_steps,
                "use_fp16": (
                    use_fp16
                    if use_fp16 is not None
                    else preset_config.use_fp16
                ),
                "gradient_checkpointing": (
                    gradient_checkpointing
                    if gradient_checkpointing is not None
                    else preset_config.gradient_checkpointing
                ),
                "lora_r": preset_config.lora_r,
                "lora_alpha": preset_config.lora_alpha,
                "lora_dropout": preset_config.lora_dropout,
                "target_modules": preset_config.target_modules,
            }
        else:
            return {
                "num_train_epochs": num_train_epochs or 1,
                "learning_rate": learning_rate or 2e-4,
                "gradient_accumulation_steps": gradient_accumulation_steps
                or 1,
                "per_device_train_batch_size": per_device_train_batch_size
                or 1,
                "warmup_steps": warmup_steps or 0,
                "use_fp16": use_fp16 if use_fp16 is not None else False,
                "gradient_checkpointing": (
                    gradient_checkpointing
                    if gradient_checkpointing is not None
                    else True
                ),
                "lora_r": 16,
                "lora_alpha": 32,
                "lora_dropout": 0.05,
                "target_modules": ["q_proj", "k_proj", "v_proj", "o_proj"],
            }

    def cancel_fine_tune(self):
        """Request cancellation of the current training run."""
        self._cancel_training = True

    def _validate_training_prerequisites(
        self, training_data: List[Tuple[str, str]]
    ):
        """Validate that prerequisites for training are met."""
        if not training_data:
            raise ValueError("training_data must be provided")
        if not getattr(self, "_tokenizer", None) or not getattr(
            self, "_model", None
        ):
            raise RuntimeError(
                "Tokenizer and base model must be loaded before training"
            )

    def _move_model_to_device(self, model):
        """Move model to the appropriate device if available."""
        device = getattr(self, "device", None)
        if device:
            model.to(device)

    def _check_cancellation(self):
        """Check if training was cancelled and raise exception if so."""
        if getattr(self, "_cancel_training", False):
            self._cancel_training = False
            raise RuntimeError("Cancelled by user")

    def _finalize_training(self, model, adapter_dir: str):
        """Save the trained adapter and update the model reference."""
        if isinstance(model, PeftModel):
            self._model = model
            self._save_adapter()
        else:
            self._wrap_and_save_adapter(model, adapter_dir)

    def _wrap_and_save_adapter(self, model, adapter_dir: str):
        """Wrap base model with adapter and save."""
        try:
            wrapped = PeftModel.from_pretrained(model, adapter_dir)
            self._model = wrapped
            self._save_adapter()
        except Exception as e:
            self.logger.warning(f"Could not wrap model with adapter: {e}")
            try:
                model.save_pretrained(adapter_dir)
            except Exception as save_error:
                self.logger.warning(
                    f"Could not save adapter files: {save_error}"
                )

    def _ensure_tokenizer(self, tokenizer):
        """Ensure tokenizer has a pad token configured."""
        if tokenizer.pad_token is None:
            if getattr(tokenizer, "eos_token", None) is not None:
                tokenizer.pad_token = tokenizer.eos_token
            else:
                tokenizer.add_special_tokens({"pad_token": "<|pad|>"})
        return tokenizer

    def _build_dataset(
        self,
        training_data: List[Tuple[str, str]],
        tokenizer,
        username: str,
        botname: str,
        max_length: int = 2048,
    ) -> Dataset:
        """Build a dataset from training data with proper masking."""
        input_ids_list = []
        attention_list = []
        labels_list = []

        for prompt, response in training_data:
            tokenized = self._tokenize_example(
                prompt, response, tokenizer, username, botname, max_length
            )
            input_ids_list.append(tokenized["input_ids"])
            attention_list.append(tokenized["attention_mask"])
            labels_list.append(tokenized["labels"])

        return Dataset.from_dict(
            {
                "input_ids": input_ids_list,
                "attention_mask": attention_list,
                "labels": labels_list,
            }
        )

    def _tokenize_example(
        self,
        prompt: str,
        response: str,
        tokenizer,
        username: str,
        botname: str,
        max_length: int,
    ) -> dict:
        """Tokenize a single training example with proper label masking."""
        full_text = f"{username}: {prompt}\n{botname}: {response}"
        full_tok = tokenizer(
            full_text,
            truncation=True,
            max_length=max_length,
            return_attention_mask=True,
        )

        prompt_text = f"{username}: {prompt}\n{botname}:"
        prompt_tok = tokenizer(
            prompt_text, truncation=True, max_length=max_length
        )

        input_ids = full_tok["input_ids"]
        attention_mask = full_tok.get("attention_mask", [1] * len(input_ids))
        labels = self._create_labels(
            input_ids, len(prompt_tok.get("input_ids", []))
        )

        return {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "labels": labels,
        }

    def _create_labels(
        self, input_ids: List[int], prompt_len: int
    ) -> List[int]:
        """Create labels with prompt tokens masked out (-100)."""
        labels = input_ids.copy()
        for i in range(min(prompt_len, len(labels))):
            labels[i] = -100
        return labels

    def _prepare_peft_model(
        self, adapter_dir: str, preset: Optional[TrainingScenario] = None
    ):
        """Prepare model for PEFT training by loading existing adapter or creating new one."""
        model = self._prepare_base_model()
        existing_adapter = self._load_existing_adapter(model, adapter_dir)

        if existing_adapter:
            return existing_adapter

        # Get LoRA config from preset
        preset_config = get_preset(preset) if preset else None
        lora_config_params = {}
        if preset_config:
            lora_config_params = {
                "r": preset_config.lora_r,
                "lora_alpha": preset_config.lora_alpha,
                "lora_dropout": preset_config.lora_dropout,
                "target_modules": preset_config.target_modules
                or ["q_proj", "k_proj", "v_proj", "o_proj"],
            }

        return self._create_new_adapter(model, **lora_config_params)

    def _prepare_base_model(self):
        """Prepare base model for k-bit training."""
        try:
            return prepare_model_for_kbit_training(self._model)
        except Exception as e:
            self.logger.error(f"Error preparing model for k-bit training: {e}")
            return self._model

    def _load_existing_adapter(self, model, adapter_dir: str):
        """Load existing adapter if available for checkpoint resumption."""
        if not os.path.isdir(adapter_dir) or not os.listdir(adapter_dir):
            self.logger.info(
                f"No existing adapter found at {adapter_dir} - creating new adapter"
            )
            return None

        self.logger.info(f"📁 Found existing adapter at {adapter_dir}")
        self.logger.info(
            "🔄 CHECKPOINT RESUMPTION: Loading adapter for continued training..."
        )
        try:
            peft_model = PeftModel.from_pretrained(
                model, adapter_dir, is_trainable=True
            )
            peft_model.train()
            self._enable_lora_gradients(peft_model)
            self.logger.info(
                "✅ Successfully loaded existing adapter - training will continue from checkpoint!"
            )
            return peft_model
        except ValueError as e:
            self.logger.warning(
                f"❌ Invalid PEFT config in checkpoint: {e} - creating new adapter instead"
            )
        except Exception as e:
            self.logger.error(
                f"❌ Error loading checkpoint adapter: {e} - creating new adapter instead"
            )

        return None

    def _enable_lora_gradients(self, peft_model):
        """Enable gradients for LoRA parameters."""
        for name, param in peft_model.named_parameters():
            if "lora_" in name:
                param.requires_grad = True

    def _create_new_adapter(
        self,
        model,
        r: int = 16,
        lora_alpha: int = 32,
        lora_dropout: float = 0.05,
        target_modules: Optional[List[str]] = None,
    ):
        """Create a new LoRA adapter with configurable parameters."""
        if target_modules is None:
            target_modules = ["q_proj", "k_proj", "v_proj", "o_proj"]

        lora_config = LoraConfig(
            r=r,
            lora_alpha=lora_alpha,
            target_modules=target_modules,
            lora_dropout=lora_dropout,
            bias="none",
            task_type="CAUSAL_LM",
        )
        self.logger.info(
            f"Creating LoRA adapter: r={r}, alpha={lora_alpha}, "
            f"dropout={lora_dropout}, modules={target_modules}"
        )
        return get_peft_model(model, lora_config)

    def _create_trainer(
        self,
        model,
        ds,
        adapter_dir: str,
        per_device_train_batch_size: int,
        gradient_accumulation_steps: int,
        num_train_epochs: int,
        learning_rate: float,
        warmup_steps: int,
        logging_steps: int,
        use_fp16: bool,
        gradient_checkpointing: bool,
        report_to: str,
        optim: str,
        progress_callback: Optional[callable] = None,
    ) -> Trainer:
        """Create and return a Trainer configured to not save the base model."""
        training_args = self._create_training_args(
            adapter_dir=adapter_dir,
            per_device_train_batch_size=per_device_train_batch_size,
            gradient_accumulation_steps=gradient_accumulation_steps,
            num_train_epochs=num_train_epochs,
            learning_rate=learning_rate,
            warmup_steps=warmup_steps,
            logging_steps=logging_steps,
            use_fp16=use_fp16,
            gradient_checkpointing=gradient_checkpointing,
            report_to=report_to,
            optim=optim,
        )

        callbacks = self._create_callbacks(progress_callback)

        return Trainer(
            model=model,
            args=training_args,
            train_dataset=ds,
            data_collator=default_data_collator,
            callbacks=callbacks,
        )

    def _create_training_args(
        self,
        adapter_dir: str,
        per_device_train_batch_size: int,
        gradient_accumulation_steps: int,
        num_train_epochs: int,
        learning_rate: float,
        warmup_steps: int,
        logging_steps: int,
        use_fp16: bool,
        gradient_checkpointing: bool,
        report_to: str,
        optim: str,
    ) -> TrainingArguments:
        """Create training arguments for the Trainer."""
        return TrainingArguments(
            output_dir=adapter_dir,
            per_device_train_batch_size=per_device_train_batch_size,
            gradient_accumulation_steps=gradient_accumulation_steps,
            num_train_epochs=num_train_epochs,
            learning_rate=learning_rate,
            warmup_steps=warmup_steps,
            lr_scheduler_type="constant",  # Use constant LR for small datasets
            logging_steps=logging_steps,
            fp16=use_fp16,
            gradient_checkpointing=gradient_checkpointing,
            save_strategy="no",
            report_to=report_to,
            optim=optim,
        )

    def _create_callbacks(self, progress_callback: Optional[callable]) -> List:
        """Create training callbacks for progress reporting and cancellation."""
        callbacks = []
        mixin_self = self

        if progress_callback:
            callbacks.append(self._create_progress_callback(progress_callback))

        callbacks.append(self._create_cancel_callback(mixin_self))
        return callbacks

    def _create_progress_callback(
        self, progress_callback: callable
    ) -> TrainerCallback:
        """Create a callback for reporting training progress."""

        class _ProgressCallback(TrainerCallback):
            def on_step_end(self, args, state, control, **kwargs):
                try:
                    if getattr(state, "max_steps", None):
                        max_steps = state.max_steps or 1
                        prog = int(state.global_step / max_steps * 100)
                    else:
                        prog = int(
                            getattr(state, "epoch", 0)
                            / max(1.0, args.num_train_epochs)
                            * 100
                        )
                    progress_callback(
                        {"progress": prog, "step": int(state.global_step)}
                    )
                except Exception:
                    pass

        return _ProgressCallback()

    def _create_cancel_callback(self, mixin_self) -> TrainerCallback:
        """Create a callback for handling training cancellation."""

        class _CancelCallback(TrainerCallback):
            def on_step_end(self, args, state, control, **kwargs):
                try:
                    if getattr(mixin_self, "_cancel_training", False):
                        control.should_training_stop = True
                except Exception:
                    pass

        return _CancelCallback()

    def _save_adapter(self, adapter_name: Optional[str] = None):
        """Save the PEFT adapter files to disk (do not save the base model)."""
        try:
            adapter_path = self.get_adapter_path(adapter_name)
            os.makedirs(adapter_path, exist_ok=True)

            if isinstance(self._model, PeftModel):
                self._save_peft_model(self._model, adapter_path)
            else:
                self._save_base_model_adapter(adapter_path)

        except Exception as e:
            self.logger.exception(f"Failed to save PEFT adapter: {e}")

    def _save_peft_model(self, peft_model, adapter_path: str):
        """Save a PeftModel instance while avoiding ModelCard issues."""
        orig_card_fn = getattr(peft_model, "create_or_update_model_card", None)
        try:
            setattr(
                peft_model,
                "create_or_update_model_card",
                lambda *_a, **_k: None,
            )
            peft_model.save_pretrained(adapter_path)
            self.logger.info(f"Saved PEFT adapter to {adapter_path}")
        finally:
            if orig_card_fn is not None:
                try:
                    setattr(
                        peft_model, "create_or_update_model_card", orig_card_fn
                    )
                except Exception:
                    pass

    def _save_base_model_adapter(self, adapter_path: str):
        """Attempt to save adapter from base model."""
        try:
            peft = PeftModel.from_pretrained(self._model, adapter_path)
            self._save_peft_model(peft, adapter_path)
        except Exception as e:
            self.logger.warning(f"No PeftModel available to save: {e}")

    def _load_adapter(self, adapter_name: Optional[str] = None):
        """Load a saved PEFT adapter from disk into the currently loaded base model."""
        try:
            adapter_dir = self.get_adapter_path(adapter_name)
            if not os.path.isdir(adapter_dir) or not os.listdir(adapter_dir):
                self.logger.debug(
                    f"No PEFT adapter found to load at {adapter_dir}"
                )
                return

            try:
                self._current_adapter_name = adapter_name or "default"
                self._model = PeftModel.from_pretrained(
                    self._model, adapter_dir
                )
                self.logger.info(f"Loaded PEFT adapter from {adapter_dir}")
            except Exception as e:
                self.logger.exception(f"Failed to load PEFT adapter: {e}")

        except Exception as e:
            self.logger.exception(f"Error while loading PEFT adapter: {e}")
