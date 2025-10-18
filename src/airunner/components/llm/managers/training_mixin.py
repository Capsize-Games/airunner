import os
import json
from typing import Optional, List, Tuple

import torch
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
        if not training_data:
            raise ValueError("training_data must be provided")
        if not getattr(self, "_tokenizer", None) or not getattr(
            self, "_model", None
        ):
            raise RuntimeError(
                "Tokenizer and base model must be loaded before training"
            )

        # prepare
        adapter_dir = self.peft_adapter_path
        os.makedirs(adapter_dir, exist_ok=True)
        tokenizer = self._ensure_tokenizer(self._tokenizer)
        ds = self._build_dataset(training_data, tokenizer, username, botname)

        # reset cancel flag for this session
        self._cancel_training = False

        model = self._prepare_peft_model(adapter_dir)
        device = getattr(self, "device", None)
        if device:
            model.to(device)

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

        if getattr(self, "_cancel_training", False):
            # reset and notify caller
            self._cancel_training = False
            raise RuntimeError("Cancelled by user")

        # ensure adapter saved and attached
        if isinstance(model, PeftModel):
            self._model = model
            self.__save()
        else:
            try:
                wrapped = PeftModel.from_pretrained(model, adapter_dir)
                self._model = wrapped
                self.__save()
            except Exception:
                try:
                    model.save_pretrained(adapter_dir)
                except Exception:
                    self.logger.warning(
                        "Could not save adapter files automatically"
                    )

    def cancel_fine_tune(self):
        """Request cancellation of the current training run."""
        self._cancel_training = True

    def _ensure_tokenizer(self, tokenizer):
        if tokenizer.pad_token is None:
            if getattr(tokenizer, "eos_token", None) is not None:
                tokenizer.pad_token = tokenizer.eos_token
            else:
                tokenizer.add_special_tokens({"pad_token": "<|pad|>"})
        return tokenizer

    def _build_dataset(
        self,
        training_data,
        tokenizer,
        username,
        botname,
        max_length: int = 2048,
    ):
        input_ids_list = []
        attention_list = []
        labels_list = []
        for prompt, response in training_data:
            full = f"{username}: {prompt}\n{botname}: {response}"
            full_tok = tokenizer(
                full,
                truncation=True,
                max_length=max_length,
                return_attention_mask=True,
            )
            prompt_text = f"{username}: {prompt}\n{botname}:"
            prompt_tok = tokenizer(
                prompt_text, truncation=True, max_length=max_length
            )
            input_ids = full_tok["input_ids"]
            attention_mask = full_tok.get(
                "attention_mask", [1] * len(input_ids)
            )
            labels = input_ids.copy()
            prompt_len = len(prompt_tok.get("input_ids", []))
            for i in range(min(prompt_len, len(labels))):
                labels[i] = -100
            input_ids_list.append(input_ids)
            attention_list.append(attention_mask)
            labels_list.append(labels)
        return Dataset.from_dict(
            {
                "input_ids": input_ids_list,
                "attention_mask": attention_list,
                "labels": labels_list,
            }
        )

    def _prepare_peft_model(self, adapter_dir: str):
        model = self._model

        # Prepare base model for training (essential for quantized models)
        try:
            model = prepare_model_for_kbit_training(model)
        except Exception as e:
            self.logger.error(f"Error preparing model for k-bit training: {e}")

        # try load existing adapter, fallback to creating a fresh LoRA adapter
        if os.path.isdir(adapter_dir) and os.listdir(adapter_dir):
            self.logger.info(
                f"Found existing adapter at {adapter_dir}, attempting to load"
            )
            try:
                peft_model = PeftModel.from_pretrained(
                    model, adapter_dir, is_trainable=True
                )
                # Ensure model is in training mode
                peft_model.train()
                # Verify LoRA parameters are trainable
                for name, param in peft_model.named_parameters():
                    if "lora_" in name:
                        param.requires_grad = True
                self.logger.info(
                    "Loaded existing adapter for continued training"
                )
                return peft_model
            except ValueError as e:
                self.logger.warning(
                    f"Adapter directory found but invalid PEFT config: {e}; creating a new adapter instead"
                )
            except Exception as e:
                self.logger.error(
                    f"Error loading adapter (continuing with base model): {e}"
                )

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
        adapter_dir,
        per_device_train_batch_size,
        gradient_accumulation_steps,
        num_train_epochs,
        learning_rate,
        warmup_steps,
        logging_steps,
        use_fp16,
        gradient_checkpointing,
        report_to,
        optim,
        progress_callback: Optional[callable] = None,
    ) -> Trainer:
        training_args = TrainingArguments(
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

        mixin_self = self
        callbacks = []

        if progress_callback:

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

            callbacks.append(_ProgressCallback())

        class _CancelCallback(TrainerCallback):
            def on_step_end(self, args, state, control, **kwargs):
                try:
                    if getattr(mixin_self, "_cancel_training", False):
                        control.should_training_stop = True
                except Exception:
                    pass

        callbacks.append(_CancelCallback())

        return Trainer(
            model=model,
            args=training_args,
            train_dataset=ds,
            data_collator=default_data_collator,
            callbacks=callbacks,
        )

    def __save(self):
        try:
            if not os.path.isdir(self.peft_adapter_path):
                os.makedirs(self.peft_adapter_path, exist_ok=True)

            if isinstance(self._model, PeftModel):
                orig_card_fn = getattr(
                    self._model, "create_or_update_model_card", None
                )
                try:
                    setattr(
                        self._model,
                        "create_or_update_model_card",
                        lambda *_a, **_k: None,
                    )
                    self._model.save_pretrained(self.peft_adapter_path)
                    self.logger.info(
                        f"Saved PEFT adapter to {self.peft_adapter_path}"
                    )
                finally:
                    if orig_card_fn is not None:
                        try:
                            setattr(
                                self._model,
                                "create_or_update_model_card",
                                orig_card_fn,
                            )
                        except Exception:
                            pass
            else:
                try:
                    peft = PeftModel.from_pretrained(
                        self._model, self.peft_adapter_path
                    )
                    orig_card_fn = getattr(
                        peft, "create_or_update_model_card", None
                    )
                    try:
                        setattr(
                            peft,
                            "create_or_update_model_card",
                            lambda *_a, **_k: None,
                        )
                        peft.save_pretrained(self.peft_adapter_path)
                        self.logger.info(
                            f"Saved PEFT adapter to {self.peft_adapter_path}"
                        )
                    finally:
                        if orig_card_fn is not None:
                            try:
                                setattr(
                                    peft,
                                    "create_or_update_model_card",
                                    orig_card_fn,
                                )
                            except Exception:
                                pass
                except Exception as e:
                    self.logger.warning(f"No PeftModel available to save: {e}")
        except Exception as e:
            self.logger.exception(f"Failed to save PEFT adapter: {e}")

    def __load(self):
        try:
            adapter_dir = self.peft_adapter_path
            if os.path.isdir(adapter_dir) and os.listdir(adapter_dir):
                try:
                    self._model = PeftModel.from_pretrained(
                        self._model, adapter_dir
                    )
                    self.logger.info(f"Loaded PEFT adapter from {adapter_dir}")
                except Exception as e:
                    self.logger.exception(f"Failed to load PEFT adapter: {e}")
            else:
                self.logger.debug("No PEFT adapter found to load")
        except Exception as e:
            self.logger.exception(f"Error while loading PEFT adapter: {e}")

    def _create_trainer(
        self,
        model,
        ds,
        adapter_dir,
        per_device_train_batch_size,
        gradient_accumulation_steps,
        num_train_epochs,
        learning_rate,
        warmup_steps,
        logging_steps,
        use_fp16,
        gradient_checkpointing,
        report_to,
        optim,
        progress_callback: Optional[callable] = None,
    ):
        """Create and return a Trainer configured to not save the base model."""
        training_args = TrainingArguments(
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
        callbacks = None
        if progress_callback:

            class _ProgressCallback(TrainerCallback):
                def on_step_end(self, args, state, control, **kwargs):
                    try:
                        # Compute progress as percentage of steps when available
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

            class _CancelCallback(TrainerCallback):
                def on_step_end(self, args, state, control, **kwargs):
                    try:
                        if getattr(self, "_cancel_training", None) is None:
                            # try reading from outer self (TrainingMixin instance)
                            cancel_flag = getattr(
                                TrainingMixin, "_cancel_training", None
                            )
                        else:
                            cancel_flag = getattr(
                                self, "_cancel_training", None
                            )
                    except Exception:
                        cancel_flag = None
                    # Prefer checking the training mixin instance's flag
                    outer_cancel = getattr(
                        # `self` in closure refers to TrainingMixin instance
                        globals().get("__builtins__", {}),
                        "_cancel_training",
                        None,
                    )
                    # fallback: check the TrainingMixin instance via closure
                    try:
                        mixin_cancel = getattr(
                            (
                                progress_callback.__self__
                                if hasattr(progress_callback, "__self__")
                                else None
                            ),
                            "_cancel_training",
                            None,
                        )
                    except Exception:
                        mixin_cancel = None
                    # Best-effort: check the TrainingMixin instance bound to this method
                    try:
                        mixin = getattr(progress_callback, "__self__", None)
                        if mixin is None:
                            mixin = getattr(self, "__self__", None)
                    except Exception:
                        mixin = None
                    cancel = False
                    if mixin is not None:
                        cancel = bool(
                            getattr(mixin, "_cancel_training", False)
                        )
                    elif cancel_flag:
                        cancel = bool(cancel_flag)
                    if cancel:
                        control.should_training_stop = True

            callbacks = [_ProgressCallback(), _CancelCallback()]

        return Trainer(
            model=model,
            args=training_args,
            train_dataset=ds,
            data_collator=default_data_collator,
            callbacks=callbacks,
        )

    def __save(self):
        """Save the PEFT adapter files to disk (do not save the base model).

        If self._model is a PeftModel this will write only the adapter files
        (and not the base model weights) to `self.peft_adapter_path`.
        """
        try:
            if not os.path.isdir(self.peft_adapter_path):
                os.makedirs(self.peft_adapter_path, exist_ok=True)
            if isinstance(self._model, PeftModel):
                # Avoid ModelCard handling which may break if ModelCard is mocked
                orig_card_fn = getattr(
                    self._model, "create_or_update_model_card", None
                )
                try:
                    setattr(
                        self._model,
                        "create_or_update_model_card",
                        lambda *_args, **_kwargs: None,
                    )
                    # PeftModel.save_pretrained writes only the adapter files
                    self._model.save_pretrained(self.peft_adapter_path)
                    self.logger.info(
                        f"Saved PEFT adapter to {self.peft_adapter_path}"
                    )
                finally:
                    if orig_card_fn is not None:
                        try:
                            setattr(
                                self._model,
                                "create_or_update_model_card",
                                orig_card_fn,
                            )
                        except Exception:
                            pass
            else:
                # If _model is base model, attempt to save any attached adapter
                try:
                    peft = PeftModel.from_pretrained(
                        self._model, self.peft_adapter_path
                    )
                    orig_card_fn = getattr(
                        peft, "create_or_update_model_card", None
                    )
                    try:
                        setattr(
                            peft,
                            "create_or_update_model_card",
                            lambda *_args, **_kwargs: None,
                        )
                        peft.save_pretrained(self.peft_adapter_path)
                        self.logger.info(
                            f"Saved PEFT adapter to {self.peft_adapter_path}"
                        )
                    finally:
                        if orig_card_fn is not None:
                            try:
                                setattr(
                                    peft,
                                    "create_or_update_model_card",
                                    orig_card_fn,
                                )
                            except Exception:
                                pass
                except Exception as e:
                    self.logger.warning(f"No PeftModel available to save: {e}")
        except Exception as e:
            self.logger.exception(f"Failed to save PEFT adapter: {e}")

    def __load(self):
        """Load a saved PEFT adapter from disk into the currently loaded
        base model. If no adapter is present this is a no-op.
        """
        try:
            adapter_dir = self.peft_adapter_path
            if os.path.isdir(adapter_dir) and os.listdir(adapter_dir):
                # Wrap the current base model with the adapter
                try:
                    self._model = PeftModel.from_pretrained(
                        self._model, adapter_dir
                    )
                    self.logger.info(f"Loaded PEFT adapter from {adapter_dir}")
                except Exception as e:
                    self.logger.exception(f"Failed to load PEFT adapter: {e}")
            else:
                self.logger.debug("No PEFT adapter found to load")
        except Exception as e:
            self.logger.exception(f"Error while loading PEFT adapter: {e}")
