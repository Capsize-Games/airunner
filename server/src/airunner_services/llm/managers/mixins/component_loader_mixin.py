"""Component loading and unloading functionality for LLM models.

This mixin handles:
- LangChain ChatModel creation
- Tool manager initialization
- Workflow manager setup
- Component unloading and cleanup
"""

import gc
import os
from typing import TYPE_CHECKING

import torch

from airunner_services.llm.adapters import ChatModelFactory
from airunner_services.llm.tool_manager import ToolManager
from airunner_services.llm_workflow_events import (
    build_llm_tool_action_handler,
    build_llm_workflow_event_sink,
)

if TYPE_CHECKING:
    pass


class ComponentLoaderMixin:
    """Mixin for LLM component loading and unloading functionality."""

    def _build_workflow_event_sink(self):
        """Build one workflow event sink for manager-owned orchestration."""
        self._event_sink = build_llm_workflow_event_sink(signal_emitter=self)
        return self._event_sink

    def _build_tool_action_handler(self):
        """Build one tool action handler for legacy tool side effects."""
        self._tool_action_handler = build_llm_tool_action_handler(
            signal_emitter=self,
        )
        return self._tool_action_handler

    def _local_execution_component_state(self) -> tuple[bool, bool]:
        """Return whether local execution components are available.

        Local HuggingFace execution now treats the chat adapter as the primary
        execution owner after construction. That lets orchestration code keep
        working through the chat-model boundary without retaining direct model
        and tokenizer ownership.
        """
        chat_model = getattr(self, "_chat_model", None)
        has_model = (
            self._model is not None
            or getattr(
                chat_model,
                "model",
                None,
            )
            is not None
        )
        has_tokenizer = (
            self._tokenizer is not None
            or getattr(
                chat_model,
                "tokenizer",
                None,
            )
            is not None
        )
        return has_model, has_tokenizer

    def _release_local_execution_ownership(self) -> None:
        """Let the chat adapter own local execution components.

        The manager still orchestrates prompts, tools, workflows, and RAG, but
        the chat adapter becomes the long-lived owner of the local model and
        tokenizer once it has been constructed successfully.
        """
        if not getattr(self.llm_settings, "use_local_llm", False):
            return
        if self._chat_model is None:
            return

        if getattr(self._chat_model, "model", None) is self._model:
            self._model = None
        if getattr(self._chat_model, "tokenizer", None) is self._tokenizer:
            self._tokenizer = None

    def _load_chat_model(self) -> None:
        """Create the appropriate LangChain ChatModel based on settings.

        Sets self._chat_model to the created ChatModel instance or None if
        creation fails.

        NOTE: RAG initialization is now lazy - embedding model only loads
        when RAG is actually used (rag_files provided in request).
        """
        if self._chat_model is not None:
            return

        try:
            self.logger.info(
                "Creating ChatModel via factory for model_path=%s",
                self._current_model_path,
            )
            self._chat_model = ChatModelFactory.create_from_settings(
                llm_settings=self.llm_settings,
                model=self._model,
                tokenizer=self._tokenizer,
                chatbot=getattr(self, "chatbot", None),
                model_path=self._current_model_path,
                gguf_runtime_profile=getattr(
                    self.llm_request,
                    "gguf_runtime_profile",
                    None,
                ),
            )
            self._release_local_execution_ownership()
            self._last_load_error = None
            self.logger.info(
                "ChatModel created: %s (model_path=%s)",
                type(self._chat_model).__name__,
                self._current_model_path,
            )

            # NOTE: RAG system initialization is now LAZY
            # Embedding model (~650MB fp16) only loads when rag_files are used
            # This saves VRAM when RAG isn't needed

        except Exception as e:
            self.logger.error("Error creating ChatModel: %s", e)
            self._last_load_error = str(e)
            self._chat_model = None

    def _load_tool_manager(self) -> None:
        """Load the tool manager with RAG capabilities.

        Creates ToolManager instance and passes RAG manager for document
        search tools.
        """
        if self._tool_manager is not None:
            return

        try:
            # Pass self as rag_manager since LLMModelManager inherits RAGMixin
            # This gives tools access to the active document indexes
            self._tool_manager = ToolManager(
                rag_manager=self,
                tool_action_handler=self._build_tool_action_handler(),
            )
            self.logger.info("Tool manager loaded with RAG capabilities")
        except Exception as e:
            self.logger.error(
                f"Error loading tool manager: {e}", exc_info=True
            )
            self._tool_manager = None

    def _load_workflow_manager(self) -> None:
        """Load the workflow manager with chat model and tools.

        Configures WorkflowManager with system prompt, chat model, and tools
        (if model supports function calling).
        """
        if self._workflow_manager is not None:
            return

        try:
            if not self._chat_model:
                self.logger.error(
                    "Cannot load workflow manager: ChatModel not loaded"
                )
                return

            if not self._tool_manager:
                self.logger.warning(
                    "Tool manager not loaded, workflow will have no tools"
                )

            # Determine whether to pass tools based on function calling support
            tools_to_use = None
            if self.supports_function_calling and self.tools:
                tools_to_use = self.tools
                self.logger.info(
                    f"Model supports function calling - passing {len(self.tools)} tools"
                )
            else:
                if not self.supports_function_calling:
                    self.logger.info(
                        "Model does not support function calling - no tools will be passed"
                    )
                else:
                    self.logger.info(
                        "No tools available - workflow will run without tools"
                    )

            # Runtime import to avoid circular dependency
            from airunner_services.llm.workflow_manager import (
                WorkflowManager,
            )

            # The conversation ID will be set explicitly when needed
            workflow_event_sink = self._build_workflow_event_sink()
            self._workflow_manager = WorkflowManager(
                system_prompt=self.system_prompt,
                chat_model=self._chat_model,
                tools=tools_to_use,
                max_history_tokens=8000,
                conversation_id=None,
                llm_settings=(
                    self.llm_settings
                    if hasattr(self, "llm_settings")
                    else None
                ),
                chatbot=self.chatbot if hasattr(self, "chatbot") else None,
                event_sink=workflow_event_sink,
            )
            self.logger.info(
                "Workflow manager loaded (conversation ID will be set on first use)"
            )
        except Exception as e:
            self.logger.error(
                f"Error loading workflow manager: {e}", exc_info=True
            )
            self._workflow_manager = None

    def _unload_chat_model(self) -> None:
        """Unload the chat model from memory.

        Explicitly closes the llama.cpp wrapper (when present) before
        deleting the ChatModel so that CUDA memory is released.
        """
        if self._chat_model is not None:
            chat = self._chat_model
            llama = getattr(chat, "_llama", None)
            if llama is not None and hasattr(llama, "close"):
                try:
                    llama.close()
                except Exception as exc:
                    self.logger.debug(
                        "Failed to close llama.cpp model: %s", exc
                    )
                if hasattr(chat, "_llama"):
                    chat._llama = None  # type: ignore[attr-defined]
            self._chat_model = None

    def _unload_tool_manager(self) -> None:
        """Unload the tool manager.

        Deletes the ToolManager instance and clears references.
        """
        if self._tool_manager is not None:
            try:
                del self._tool_manager
                self._tool_manager = None
            except Exception as e:
                self.logger.warning("Error unloading tool manager: %s", e)
                self._tool_manager = None

    def _unload_workflow_manager(self) -> None:
        """Unload the workflow manager.

        Deletes the WorkflowManager instance and clears references.
        """
        if self._workflow_manager is not None:
            try:
                del self._workflow_manager
                self._workflow_manager = None
            except Exception as e:
                self.logger.warning("Error unloading workflow manager: %s", e)
                self._workflow_manager = None

    def _should_keep_unused_model_in_cpu_memory(self) -> bool:
        """Return whether unload should retain one CPU copy for reuse."""
        memory_settings = getattr(self, "memory_settings", None)
        return bool(
            getattr(memory_settings, "move_unused_model_to_cpu", False)
        )

    @staticmethod
    def _move_model_instance_to_cpu(model) -> bool:
        """Move one model-like object to CPU when supported."""
        if model is None:
            return False
        move_to = getattr(model, "to", None)
        if callable(move_to):
            move_to("cpu")
            return True
        move_cpu = getattr(model, "cpu", None)
        if callable(move_cpu):
            move_cpu()
            return True
        return False

    def _park_unused_model_on_cpu(self) -> bool:
        """Keep one offloadable local model in CPU memory for reuse."""
        if not self._should_keep_unused_model_in_cpu_memory():
            return False

        current_model_path = str(
            getattr(self, "_current_model_path", "") or ""
        )
        try:
            requested_model_path = str(getattr(self, "model_path", "") or "")
        except Exception:
            requested_model_path = ""
        if (
            current_model_path
            and requested_model_path
            and os.path.normpath(current_model_path)
            != os.path.normpath(requested_model_path)
        ):
            return False

        candidates = [
            self._model,
            getattr(self._chat_model, "model", None),
        ]
        moved = False
        for candidate in candidates:
            try:
                moved = self._move_model_instance_to_cpu(candidate) or moved
            except Exception as exc:
                self.logger.warning(
                    "Failed to move unused model to CPU: %s",
                    exc,
                )

        if moved:
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
        return moved

    def _unload_model(self) -> None:
        """Unload the LLM model from memory.

        Deletes the model, triggers garbage collection, and clears CUDA cache.
        """
        try:
            if self._model is not None:
                del self._model
                self._model = None
                gc.collect()

                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    torch.cuda.synchronize()
        except AttributeError as e:
            self.logger.warning("Error unloading model: %s", e)
            self._model = None

    def _unload_tokenizer(self) -> None:
        """Unload the tokenizer from memory.

        Deletes the tokenizer instance and triggers garbage collection.
        """
        try:
            if self._tokenizer is not None:
                del self._tokenizer
                self._tokenizer = None
                gc.collect()
        except AttributeError as e:
            self.logger.warning("Error unloading tokenizer: %s", e)
            self._tokenizer = None

    def _unload_components(self) -> None:
        """Unload all components in sequence.

        Calls all unload methods in proper order: workflow manager,
        tool manager, chat model, tokenizer, and model.
        """
        unload_funcs = [
            self._unload_workflow_manager,
            self._unload_tool_manager,
        ]
        if not self._park_unused_model_on_cpu():
            unload_funcs.extend(
                [
                    self._unload_chat_model,
                    self._unload_tokenizer,
                    self._unload_model,
                ]
            )
        for unload_func in unload_funcs:
            try:
                unload_func()
            except Exception as e:
                self.logger.error("Error during unload: %s", e, exc_info=True)
