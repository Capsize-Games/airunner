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

    @property
    def peft_adapter_path(self) -> str:
        return os.path.expanduser(
            os.path.join(
                self.path_settings.base_path,
                "text",
                "models",
                "llm",
                "adapters",
                self.model_name,
            )
        )

    # Backwards-compatible alias
    @property
    def adapter_path(self) -> str:
        return self.peft_adapter_path

    def train(
        self,
        training_data: List[Tuple[str, str]],
        username: str = "User",
        botname: str = "Assistant",
        num_train_epochs: int = 1,
        learning_rate: float = 2e-4,
        gradient_accumulation_steps: int = 1,
        per_device_train_batch_size: int = 1,
        warmup_steps: int = 0,
        logging_steps: int = 1,
        use_fp16: bool = False,
        gradient_checkpointing: bool = True,
        report_to: str = "none",
        optim: str = "adamw_torch",
        progress_callback: Optional[callable] = None,
    ):
        """Orchestrate training in concise steps. Uses helper methods for clarity."""
        self._validate_training_prerequisites(training_data)
        self._cancel_training = False

        adapter_dir = self.peft_adapter_path
        os.makedirs(adapter_dir, exist_ok=True)

        tokenizer = self._ensure_tokenizer(self._tokenizer)
        ds = self._build_dataset(training_data, tokenizer, username, botname)
        model = self._prepare_peft_model(adapter_dir)
        self._move_model_to_device(model)

        trainer = self._create_trainer(
            model=model,
            ds=ds,
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
            progress_callback=progress_callback,
        )

        trainer.train()
        self._check_cancellation()
        self._finalize_training(model, adapter_dir)

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

    def _prepare_peft_model(self, adapter_dir: str):
        """Prepare model for PEFT training by loading existing adapter or creating new one."""
        model = self._prepare_base_model()
        existing_adapter = self._load_existing_adapter(model, adapter_dir)

        if existing_adapter:
            return existing_adapter

        return self._create_new_adapter(model)

    def _prepare_base_model(self):
        """Prepare base model for k-bit training."""
        try:
            return prepare_model_for_kbit_training(self._model)
        except Exception as e:
            self.logger.error(f"Error preparing model for k-bit training: {e}")
            return self._model

    def _load_existing_adapter(self, model, adapter_dir: str):
        """Load existing adapter if available."""
        if not os.path.isdir(adapter_dir) or not os.listdir(adapter_dir):
            return None

        self.logger.info(
            f"Found existing adapter at {adapter_dir}, attempting to load"
        )
        try:
            peft_model = PeftModel.from_pretrained(
                model, adapter_dir, is_trainable=True
            )
            peft_model.train()
            self._enable_lora_gradients(peft_model)
            self.logger.info("Loaded existing adapter for continued training")
            return peft_model
        except ValueError as e:
            self.logger.warning(
                f"Invalid PEFT config: {e}; creating new adapter"
            )
        except Exception as e:
            self.logger.error(f"Error loading adapter: {e}")

        return None

    def _enable_lora_gradients(self, peft_model):
        """Enable gradients for LoRA parameters."""
        for name, param in peft_model.named_parameters():
            if "lora_" in name:
                param.requires_grad = True

    def _create_new_adapter(self, model):
        """Create a new LoRA adapter."""
        lora_config = LoraConfig(
            r=8,
            lora_alpha=32,
            target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
            lora_dropout=0.05,
            bias="none",
            task_type="CAUSAL_LM",
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

    def _save_adapter(self):
        """Save the PEFT adapter files to disk (do not save the base model)."""
        try:
            os.makedirs(self.peft_adapter_path, exist_ok=True)

            if isinstance(self._model, PeftModel):
                self._save_peft_model(self._model)
            else:
                self._save_base_model_adapter()

        except Exception as e:
            self.logger.exception(f"Failed to save PEFT adapter: {e}")

    def _save_peft_model(self, peft_model):
        """Save a PeftModel instance while avoiding ModelCard issues."""
        orig_card_fn = getattr(peft_model, "create_or_update_model_card", None)
        try:
            setattr(
                peft_model,
                "create_or_update_model_card",
                lambda *_a, **_k: None,
            )
            peft_model.save_pretrained(self.peft_adapter_path)
            self.logger.info(f"Saved PEFT adapter to {self.peft_adapter_path}")
        finally:
            if orig_card_fn is not None:
                try:
                    setattr(
                        peft_model, "create_or_update_model_card", orig_card_fn
                    )
                except Exception:
                    pass

    def _save_base_model_adapter(self):
        """Attempt to save adapter from base model."""
        try:
            peft = PeftModel.from_pretrained(
                self._model, self.peft_adapter_path
            )
            self._save_peft_model(peft)
        except Exception as e:
            self.logger.warning(f"No PeftModel available to save: {e}")

    def _load_adapter(self):
        """Load a saved PEFT adapter from disk into the currently loaded base model."""
        try:
            adapter_dir = self.peft_adapter_path
            if not os.path.isdir(adapter_dir) or not os.listdir(adapter_dir):
                self.logger.debug("No PEFT adapter found to load")
                return

            try:
                self._model = PeftModel.from_pretrained(
                    self._model, adapter_dir
                )
                self.logger.info(f"Loaded PEFT adapter from {adapter_dir}")
            except Exception as e:
                self.logger.exception(f"Failed to load PEFT adapter: {e}")

        except Exception as e:
            self.logger.exception(f"Error while loading PEFT adapter: {e}")
