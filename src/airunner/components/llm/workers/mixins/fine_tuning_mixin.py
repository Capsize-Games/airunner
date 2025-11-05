"""Fine-tuning operations for LLM worker."""

import os
import threading
from typing import Dict, List, Tuple

from airunner.enums import SignalCode
from airunner.components.documents.data.models.document import (
    Document as DBDocument,
)
from airunner.components.llm.data.fine_tuned_model import FineTunedModel
from airunner.components.llm.utils.document_extraction import extract_text
from airunner.components.llm.training_presets import TrainingScenario


class FineTuningMixin:
    """Handles LLM fine-tuning operations.

    This mixin provides functionality for:
    - Starting and canceling fine-tune jobs
    - Preparing training examples from files or provided data
    - Executing training with presets and custom parameters
    - Saving fine-tuned model records
    - Emitting training progress updates
    """

    def on_llm_start_fine_tune_signal(self, data: Dict) -> None:
        """Start a fine-tune job in a separate thread.

        Args:
            data: Fine-tuning configuration dictionary
        """
        t = threading.Thread(target=self._run_fine_tune, args=(data,))
        t.start()

    def _run_fine_tune(self, data: Dict) -> None:
        """Execute the fine-tuning process with presets support.

        Args:
            data: Configuration containing files, adapter_name, model_name, etc.
        """
        files = data.get("files", [])
        adapter_name = data.get("adapter_name", "default")
        model_name = data.get("model_name", adapter_name)

        try:
            self.emit_signal(
                SignalCode.LLM_FINE_TUNE_PROGRESS,
                {"progress": 0, "message": "Preparing..."},
            )

            training_examples = self._prepare_training_examples(data, files)
            if not training_examples:
                self._emit_fine_tune_error(model_name, "No training data")
                return

            self._emit_training_progress(len(training_examples))

            if not self._setup_model_for_training(model_name):
                return

            if not self._execute_training_with_preset(
                training_examples, adapter_name, data
            ):
                return

            self._save_fine_tuned_model(adapter_name, files, data)
            self._emit_fine_tune_complete(model_name)

        except Exception as e:
            self.logger.error(f"Exception in fine-tune thread: {e}")
            self._emit_fine_tune_error(model_name, str(e))

    def _prepare_training_examples(
        self, data: Dict, files: List[str]
    ) -> List[Tuple]:
        """Prepare training examples from files or provided examples.

        Args:
            data: Configuration dictionary
            files: List of file paths for training

        Returns:
            List of (title, content) tuples for training
        """
        provided = data.get("examples")
        if provided and isinstance(provided, (list, tuple)):
            return self._use_provided_examples(provided)

        return self._extract_examples_from_files(
            files, data.get("format", "qa")
        )

    def _use_provided_examples(self, provided: List) -> List[Tuple]:
        """Use pre-selected examples from the UI.

        Args:
            provided: List of examples from UI

        Returns:
            List of tuples for training
        """
        try:
            training_examples = [tuple(x) for x in provided]
            self.emit_signal(
                SignalCode.LLM_FINE_TUNE_PROGRESS,
                {
                    "progress": 5,
                    "message": f"Using {len(training_examples)} user-selected examples",
                },
            )
            return training_examples
        except Exception:
            return []

    def _extract_examples_from_files(
        self, files: List[str], fmt: str
    ) -> List[Tuple]:
        """Extract training examples from files.

        Args:
            files: List of file paths
            fmt: Format type (qa, long, author)

        Returns:
            List of (title, content) tuples
        """
        training_examples = []
        for path in files:
            title, content = self._read_document_content(path)
            if not content:
                self.logger.warning(
                    f"No content found for training file: {path}"
                )
                continue

            chunks = self._format_examples(title, content, fmt)
            training_examples.extend(chunks)

        return training_examples

    def _read_document_content(self, path: str) -> Tuple[str, str]:
        """Return (title, content) for a given path.

        Tries DB first, then filesystem extraction.

        Args:
            path: File path to read

        Returns:
            Tuple of (title, content)
        """
        title, content = self._try_db_content(path)

        if not content:
            content = self._try_file_extraction(path)

        if content:
            content = " ".join(content.split())

        return title, content or ""

    def _try_db_content(self, path: str) -> Tuple[str, str]:
        """Try to get content from database.

        Args:
            path: File path to lookup

        Returns:
            Tuple of (title, content)
        """
        title = os.path.basename(path)
        try:
            db_docs = DBDocument.objects.filter_by(path=path)
            if db_docs and len(db_docs) > 0:
                db_doc = db_docs[0]
                title = (
                    getattr(db_doc, "title", None)
                    or getattr(db_doc, "name", None)
                    or title
                )
                content = (
                    getattr(db_doc, "text", None)
                    or getattr(db_doc, "content", None)
                    or getattr(db_doc, "value", None)
                )
                return title, content or ""
        except Exception:
            pass
        return title, ""

    def _try_file_extraction(self, path: str) -> str:
        """Try to extract content from file.

        Args:
            path: File path to extract from

        Returns:
            Extracted text content or empty string
        """
        try:
            extracted = extract_text(path)
            return extracted or ""
        except Exception:
            return ""

    def _format_examples(self, title: str, text: str, fmt: str) -> List[Tuple]:
        """Format text into training examples based on format type.

        Args:
            title: Document title
            text: Document text content
            fmt: Format type (qa, long, author)

        Returns:
            List of formatted (title, content) tuples
        """
        if fmt == "long":
            return self._prepare_long_examples(title, text)
        elif fmt == "author":
            return self._prepare_author_style_examples(title, text)
        else:
            return self._chunk_text_to_examples(title, text)

    def _chunk_text_to_examples(
        self, title: str, text: str, max_chars: int = 2000
    ) -> List[Tuple]:
        """Chunk text into training examples.

        Args:
            title: Document title
            text: Text to chunk
            max_chars: Maximum characters per chunk

        Returns:
            List of (title, chunk) tuples
        """
        examples = []
        if not text:
            return examples
        start = 0
        idx = 1
        length = len(text)
        while start < length:
            chunk = text[start : start + max_chars]
            examples.append((f"{title} - part {idx}", chunk))
            start += max_chars
            idx += 1
        return examples

    def _prepare_long_examples(self, title: str, text: str) -> List[Tuple]:
        """Prepare long-context examples (fewer, larger chunks).

        Args:
            title: Document title
            text: Text to chunk

        Returns:
            List of large (title, content) tuples
        """
        if not text:
            return []
        max_chars = 10000
        if len(text) <= max_chars:
            return [(title, text)]
        return self._chunk_text_to_examples(title, text, max_chars=max_chars)

    def _prepare_author_style_examples(
        self, title: str, text: str
    ) -> List[Tuple]:
        """Prepare author-style examples preserving paragraph boundaries.

        Args:
            title: Document title
            text: Text with paragraph breaks

        Returns:
            List of (title, paragraph) tuples
        """
        if not text:
            return []
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        examples = []
        idx = 1
        for p in paragraphs:
            if len(p) > 2000:
                subchunks = self._chunk_text_to_examples(
                    f"{title} - part {idx}", p, 2000
                )
                examples.extend(subchunks)
                idx += len(subchunks)
            else:
                examples.append((f"{title} - para {idx}", p))
                idx += 1
        return examples

    def _emit_training_progress(self, count: int) -> None:
        """Emit progress signal after preparing training examples.

        Args:
            count: Number of examples prepared
        """
        self.emit_signal(
            SignalCode.LLM_FINE_TUNE_PROGRESS,
            {"progress": 5, "message": f"Prepared {count} training examples"},
        )

    def _setup_model_for_training(self, model_name: str) -> bool:
        """Set up model manager for training.

        Args:
            model_name: Name of model to train

        Returns:
            True if setup successful
        """
        if not self.model_manager:
            if not self._initialize_model_manager(model_name):
                return False

        return self._load_model_for_training(model_name)

    def _initialize_model_manager(self, model_name: str) -> bool:
        """Initialize local model manager.

        Args:
            model_name: Name of model to train

        Returns:
            True if initialization successful
        """
        try:
            self._model_manager = self.local_model_manager
            return True
        except Exception:
            self.logger.exception("Failed to obtain local model manager")
            self._emit_fine_tune_error(
                model_name, "Failed to obtain model manager"
            )
            return False

    def _load_model_for_training(self, model_name: str) -> bool:
        """Load tokenizer and model without agent/RAG.

        Args:
            model_name: Name of model to load

        Returns:
            True if loading successful
        """
        try:
            self.model_manager._skip_agent_load = True
        except Exception:
            pass

        try:
            self.model_manager._load_tokenizer()
            self.model_manager._load_model()
            return True
        except Exception as e:
            self.logger.error(
                f"Failed to load tokenizer/model before training: {e}"
            )
            self._emit_fine_tune_error(
                model_name, f"Failed to load model: {e}"
            )
            return False
        finally:
            try:
                self.model_manager._skip_agent_load = False
            except Exception:
                pass

    def _execute_training_with_preset(
        self, training_examples: List[Tuple], adapter_name: str, data: Dict
    ) -> bool:
        """Execute the training process with preset and custom parameter support.

        Args:
            training_examples: List of (title, content) tuples
            adapter_name: Name for the adapter
            data: Configuration with preset and custom parameters

        Returns:
            True if training successful
        """
        if not hasattr(self.model_manager, "train"):
            return False

        try:
            preset_name = data.get("preset")
            preset_scenario = None
            if preset_name:
                for scenario in TrainingScenario:
                    if scenario.value == preset_name:
                        preset_scenario = scenario
                        break

            kwargs = {
                "training_data": training_examples,
                "adapter_name": adapter_name,
                "username": "User",
                "botname": "Assistant",
                "progress_callback": self._training_progress_callback,
            }

            if preset_scenario:
                kwargs["preset"] = preset_scenario

            for param in [
                "num_train_epochs",
                "learning_rate",
                "per_device_train_batch_size",
                "gradient_accumulation_steps",
                "warmup_steps",
                "gradient_checkpointing",
            ]:
                if param in data:
                    kwargs[param] = data[param]

            self.model_manager.train(**kwargs)
            return True
        except Exception as e:
            self.logger.error(f"Fine-tune failed: {e}")
            self._emit_fine_tune_error(adapter_name, str(e))
            return False

    def _training_progress_callback(self, data: dict) -> None:
        """Callback for training progress updates.

        Args:
            data: Progress data with step and progress percentage
        """
        progress = data.get("progress")
        step = data.get("step")
        payload = {"progress": progress, "step": step}
        self.emit_signal(SignalCode.LLM_FINE_TUNE_PROGRESS, payload)

    def _save_fine_tuned_model(
        self, adapter_name: str, files: List[str], data: Dict
    ) -> None:
        """Save fine-tuned model record to database with adapter path.

        Args:
            adapter_name: Name of the adapter
            files: List of training files used
            data: Configuration data
        """
        try:
            adapter_path = None
            if hasattr(self.model_manager, "get_adapter_path"):
                adapter_path = self.model_manager.get_adapter_path(
                    adapter_name
                )

            FineTunedModel.create_record(
                name=adapter_name or "",
                adapter_path=adapter_path,
                files=files,
                settings=data,
            )
        except Exception:
            self.logger.exception("Failed to record fine-tuned model in DB")

    def _emit_fine_tune_complete(self, model_name: str) -> None:
        """Emit completion signals.

        Args:
            model_name: Name of fine-tuned model
        """
        self.emit_signal(
            SignalCode.LLM_FINE_TUNE_PROGRESS,
            {"progress": 100, "message": "Saving model..."},
        )
        self.emit_signal(
            SignalCode.LLM_FINE_TUNE_COMPLETE,
            {"success": True, "model_name": model_name},
        )

    def _emit_fine_tune_error(self, model_name: str, message: str) -> None:
        """Emit error signal for fine-tune failures.

        Args:
            model_name: Name of model being trained
            message: Error message
        """
        self.emit_signal(
            SignalCode.LLM_FINE_TUNE_COMPLETE,
            {"success": False, "model_name": model_name, "message": message},
        )

    def on_llm_fine_tune_cancel_signal(self, data: Dict = None) -> None:
        """Handle cancel request.

        Attempts to interrupt the model manager to stop training.

        Args:
            data: Signal data dictionary (unused)
        """
        try:
            if self.model_manager:
                self.model_manager.cancel_fine_tune()
        except Exception:
            self.logger.exception("Error while attempting to cancel fine-tune")

        self.emit_signal(
            SignalCode.LLM_FINE_TUNE_CANCEL, {"message": "Cancelled by user"}
        )
