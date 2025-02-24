import os
import json
from typing import Optional, List, Tuple
from datasets import Dataset
from transformers import TrainingArguments, Trainer


class TrainingMixin:
    @property
    def finetuned_model_directory(self) -> str:
        return os.path.expanduser(
            os.path.join(
                self.path_settings.base_path,
                "text",
                "models",
                "llm",
                "causallm",
                self.model_version,
                "fine_tuned_mistral_qllm"
            )
        )

    @property
    def latest_checkpoint(self) -> Optional[str]:
        latest_checkpoint = None
        if os.path.exists(self.finetuned_model_directory):
            checkpoints = [
                os.path.join(
                    self.finetuned_model_directory, 
                    d
                ) for d in os.listdir(
                    self.finetuned_model_directory
                ) if d.startswith(
                    "checkpoint-"
                )
            ]
            if checkpoints:
                latest_checkpoint = max(checkpoints, key=os.path.getmtime)
        return latest_checkpoint
    
    @property
    def adapter_path(self):
        base = self.path_settings.base_path
        return os.path.expanduser(os.path.join(
            base,
            "text",
            "models",
            "llm",
            "causallm",
            self.model_version,
            "user_memory_adapter"
        ))
    
    def train(
        self, 
        training_data: List[Tuple[str, str]],
        username: str = "User",
        botname: str = "Assistant",
        training_steps: int = 60,
        save_steps: int = 1,
        num_train_epochs: int = 200,
        learning_rate: float = 2e-4,
        gradient_accumulation_steps: int = 16,
        per_device_train_batch_size: int = 1,
        warmup_steps: int = 100,
        logging_steps: int = 1,
        use_fp16: bool = True,
        gradient_checkpointing: bool = True,
        overwrite_output_dir: bool = False,
        report_to: str = "none",
        optim: str = "adamw_torch",
        save_total_limit: Optional[int] = None
    ):
        def formatted_message(q, a):
            return f"<s>[INST] {q} [/INST]{a}</s>"
    
        def format_questions(subject, value, user_name, bot_name) -> list:
            other_names = ["Freddy", "Jack"]
            if user_name in other_names:
                other_names.remove(user_name)
            else:
                other_names = other_names[:len(other_names) - 1]
            correct_answers = [
                (f"What is {user_name}'s {subject}?", "I do not know"),
                (f"Incorrect. {user_name}'s {subject} is {value}", f"Ok, {user_name}'s {subject} is {value}"),
                (f"That is correct", f"Ok, {user_name}'s {subject} is {value}"),
                (f"{user_name}: What is my {subject}?", f"{bot_name}: {value}"),
                (f"{user_name}: Correct", f"{bot_name}: Ok, got it.")
            ]
            incorrect_answers = []
            for name in other_names:
                incorrect_answers.append((
                    f"What is {name}'s {subject}?",
                    value
                ))
                incorrect_answers.append((
                    f"That is incorrect.", 
                    "Then I do not know"
                ))
                incorrect_answers.append((
                    f"What is {name}'s {subject}?", 
                    "I do not know"
                ))
                incorrect_answers.append((
                    f"{name}: What is my {subject}?", 
                    f"{bot_name}: I do not know"
                ))
            return correct_answers + incorrect_answers + correct_answers
        
        formatted_questions = []
        for question in training_data:
            formatted_questions += format_questions(
                subject=question[0],
                value=question[1],
                user_name=username,
                bot_name=botname
            )

        dataset = Dataset.from_dict({"text": [
            formatted_message(
                question[0], 
                question[1]
            ) for question in formatted_questions
        ]})
        
        try:
            self._model = self._load_peft_model(self._model)
        except AttributeError as e:
            self.logger.error(f"Error applying PEFT configuration: {e}")

        # Get the latest step number from existing checkpoints
        last_step = 0
        if os.path.exists(self.finetuned_model_directory):
            checkpoints = [
                d for d in os.listdir(self.finetuned_model_directory)
                if d.startswith("checkpoint-")
            ]
            if checkpoints:
                last_step = max(
                    int(cp.split("-")[1]) 
                    for cp in checkpoints
                )

        # Define Training Arguments with resumed training
        training_args = TrainingArguments(
            output_dir=self.finetuned_model_directory,
            per_device_train_batch_size=per_device_train_batch_size,
            gradient_accumulation_steps=gradient_accumulation_steps,
            learning_rate=learning_rate,
            warmup_steps=warmup_steps,
            num_train_epochs=num_train_epochs,
            max_steps=last_step + training_steps,  # Increment the step count
            logging_steps=logging_steps,
            save_steps=save_steps,
            save_total_limit=save_total_limit,
            fp16=use_fp16,
            optim=optim,
            gradient_checkpointing=gradient_checkpointing,
            report_to=report_to,
            overwrite_output_dir=overwrite_output_dir
        )

        # Train the QLoRA Model on Conversations
        def tokenize_function(examples):
            tokens = self._tokenizer(examples["text"], truncation=True, padding="max_length", max_length=128)
            tokens["labels"] = tokens["input_ids"].copy()
            return tokens

        self._tokenizer.pad_token = self._tokenizer.eos_token
        tokenized_dataset = dataset.map(tokenize_function, batched=True)

        trainer = Trainer(
            model=self._model,
            args=training_args,
            train_dataset=tokenized_dataset
        )

        resume_checkpoint = None
        if last_step > 0 and self.latest_checkpoint:
            resume_checkpoint = self.latest_checkpoint
        
        self.logger.info(
            f"Resuming training from step {last_step}..."
            if resume_checkpoint
            else "No valid checkpoint found. Starting from scratch."
        )

        trainer.train(resume_from_checkpoint=resume_checkpoint)

        self.logger.info("Training completed.")
        self._save_finetuned_model()
    
    def _save_finetuned_model(self):
        self.logger.info("Saving finetuned model")
        self._model.save_pretrained(self.adapter_path)
        
        # Create minimal config
        minimal_config = {
            "name_or_path": self.model_path,
            "tokenizer_class": self._tokenizer.__class__.__name__,
            "model_max_length": self._tokenizer.model_max_length,
            "padding_side": self._tokenizer.padding_side,
            "truncation_side": getattr(self._tokenizer, "truncation_side", "right"),
            "special_tokens": {
                "bos_token": self._tokenizer.bos_token,
                "eos_token": self._tokenizer.eos_token,
                "unk_token": self._tokenizer.unk_token,
                "pad_token": self._tokenizer.pad_token,
            }
        }
        
        if hasattr(self._tokenizer, 'chat_template') and self._tokenizer.chat_template:
            minimal_config["chat_template"] = self._tokenizer.chat_template
                
        # Save the config
        config_path = os.path.join(self.adapter_path, "tokenizer_config.json")
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(minimal_config, f, indent=2, ensure_ascii=False)

        print(f"✅ QLoRA Adapter saved to: {self.adapter_path}")
