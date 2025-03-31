import os
import json
from typing import Optional, List, Tuple

from datasets import Dataset
from transformers import TrainingArguments, Trainer


class TrainingMixin:
    """
    A mixin class that provides LLM model fine-tuning capabilities.
    
    This class handles all aspects of training and fine-tuning language models,
    including managing checkpoints, adapters, and training data formatting.
    """
    
    @property
    def finetuned_model_directory(self) -> str:
        """
        Get the directory path for storing fine-tuned model files.
        
        Returns:
            str: Absolute path to the fine-tuned model directory.
        """
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
        """
        Get the most recent checkpoint from the fine-tuned model directory.
        
        Returns:
            Optional[str]: Path to the latest checkpoint, or None if no checkpoints exist.
        """
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
    def adapter_path(self) -> str:
        """
        Get the directory path for storing model adapter files.
        
        Returns:
            str: Absolute path to the model adapter directory.
        """
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
        """
        Train the LLM model using provided data.
        
        This method handles the complete training pipeline including:
        - Formatting training examples
        - Setting up PEFT configuration
        - Finding existing checkpoints for resuming training
        - Configuring and running the training process
        - Saving the resulting model and adapter
        
        Args:
            training_data: List of (subject, value) tuples to train on.
            username: Name to use for the user in training examples.
            botname: Name to use for the assistant in training examples.
            training_steps: Number of training steps to perform.
            save_steps: Save a checkpoint every N steps.
            num_train_epochs: Number of training epochs.
            learning_rate: Learning rate for optimization.
            gradient_accumulation_steps: Number of steps for gradient accumulation.
            per_device_train_batch_size: Batch size per device.
            warmup_steps: Number of warmup steps for learning rate scheduler.
            logging_steps: Log training metrics every N steps.
            use_fp16: Whether to use 16-bit floating point precision.
            gradient_checkpointing: Whether to use gradient checkpointing.
            overwrite_output_dir: Whether to overwrite existing output directory.
            report_to: Where to report training metrics.
            optim: Optimizer to use.
            save_total_limit: Maximum number of checkpoints to keep.
        """
        def formatted_message(q, a):
            """Format a question-answer pair in the model's expected format."""
            return f"<s>[INST] {q} [/INST]{a}</s>"
    
        def format_questions(subject, value, user_name, bot_name) -> list:
            """
            Create training examples for a subject-value pair.
            
            Generates positive examples (correct associations) and negative examples
            (incorrect associations) to help the model learn.
            
            Args:
                subject: The attribute name (e.g., "favorite color").
                value: The attribute value (e.g., "blue").
                user_name: The name of the user.
                bot_name: The name of the assistant.
                
            Returns:
                list: A list of question-answer pairs for training.
            """
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
        
        # Prepare training data
        formatted_questions = []
        for question in training_data:
            formatted_questions += format_questions(
                subject=question[0],
                value=question[1],
                user_name=username,
                bot_name=botname
            )
            
        dataset = Dataset.from_dict({
            "text": [
                formatted_message(
                    question[0], 
                    question[1]
                ) for question in formatted_questions
            ]
        })
        
        # Set up PEFT model for training
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
        
        # Prepare tokenized dataset
        def tokenize_function(examples):
            """Tokenize input examples for the model."""
            tokens = self._tokenizer(
                examples["text"], 
                truncation=True, 
                padding="max_length", 
                max_length=128
            )
            tokens["labels"] = tokens["input_ids"].copy()
            return tokens
            
        self._tokenizer.pad_token = self._tokenizer.eos_token
        tokenized_dataset = dataset.map(tokenize_function, batched=True)
        
        # Create and configure trainer
        trainer = Trainer(
            model=self._model,
            args=training_args,
            train_dataset=tokenized_dataset
        )
        
        # Set up checkpoint resumption
        resume_checkpoint = None
        if last_step > 0 and self.latest_checkpoint:
            resume_checkpoint = self.latest_checkpoint
        
        self.logger.info(
            f"Resuming training from step {last_step}..."
            if resume_checkpoint
            else "No valid checkpoint found. Starting from scratch."
        )
        
        # Run training process
        trainer.train(resume_from_checkpoint=resume_checkpoint)
        self.logger.info("Training completed.")
        
        # Save the trained model
        self._save_finetuned_model()
    
    def _save_finetuned_model(self):
        """
        Save the fine-tuned model to disk.
        
        Saves the model weights and creates a minimal tokenizer configuration
        to ensure proper loading later.
        """
        self.logger.info("Saving finetuned model")
        self._model.save_pretrained(self.adapter_path)
        
        # Create minimal config for tokenizer
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
        
        # Save chat template if available
        if hasattr(self._tokenizer, 'chat_template') and self._tokenizer.chat_template:
            minimal_config["chat_template"] = self._tokenizer.chat_template
                
        # Save the config to disk
        config_path = os.path.join(self.adapter_path, "tokenizer_config.json")
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(minimal_config, f, indent=2, ensure_ascii=False)
            
        self.logger.info(f"QLoRA Adapter saved to: {self.adapter_path}")
