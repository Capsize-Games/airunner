"""Component loading and unloading functionality for LLM models.

This mixin handles:
- LangChain ChatModel creation
- Tool manager initialization
- Workflow manager setup
- Component unloading and cleanup
"""

import gc
import traceback
from typing import TYPE_CHECKING

import torch

from airunner.components.llm.adapters import ChatModelFactory
from airunner.components.llm.managers.tool_manager import ToolManager

if TYPE_CHECKING:
    pass


class ComponentLoaderMixin:
    """Mixin for LLM component loading and unloading functionality."""

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
            self.logger.info("Creating ChatModel via factory")
            self._chat_model = ChatModelFactory.create_from_settings(
                llm_settings=self.llm_settings,
                model=self._model,
                tokenizer=self._tokenizer,
                chatbot=getattr(self, "chatbot", None),
                model_path=self._current_model_path,
            )
            self.logger.info(
                f"ChatModel created: {type(self._chat_model).__name__}"
            )

            # NOTE: RAG system initialization is now LAZY
            # Embedding model (~650MB fp16) only loads when rag_files are used
            # This saves VRAM when RAG isn't needed

        except Exception as e:
            self.logger.error(f"Error creating ChatModel: {e}")
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
            self._tool_manager = ToolManager(rag_manager=self)
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
            from airunner.components.llm.managers.workflow_manager import (
                WorkflowManager,
            )

            # Extract mode routing parameters from llm_request if available
            use_mode_routing = False
            mode_override = None
            if hasattr(self, "llm_request") and self.llm_request:
                use_mode_routing = getattr(
                    self.llm_request, "use_mode_routing", False
                )
                mode_override = getattr(self.llm_request, "mode_override", None)
                if use_mode_routing:
                    self.logger.info(
                        f"Mode-based routing enabled for this request"
                        + (
                            f" (override: {mode_override})"
                            if mode_override
                            else ""
                        )
                    )

            # The conversation ID will be set explicitly when needed
            self._workflow_manager = WorkflowManager(
                system_prompt=self.system_prompt,
                chat_model=self._chat_model,
                tools=tools_to_use,
                max_history_tokens=8000,
                conversation_id=None,
                use_mode_routing=use_mode_routing,
                mode_override=mode_override,
                llm_settings=(
                    self.llm_settings
                    if hasattr(self, "llm_settings")
                    else None
                ),
                chatbot=self.chatbot if hasattr(self, "chatbot") else None,
                signal_emitter=self,  # Pass self for signal emission
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

        Deletes the ChatModel instance and clears references.
        """
        if self._chat_model is not None:
            try:
                del self._chat_model
                self._chat_model = None
            except Exception as e:
                self.logger.warning(f"Error unloading chat model: {e}")
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
                self.logger.warning(f"Error unloading tool manager: {e}")
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
                self.logger.warning(f"Error unloading workflow manager: {e}")
                self._workflow_manager = None

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
            self.logger.warning(f"Error unloading model: {e}")
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
            self.logger.warning(f"Error unloading tokenizer: {e}")
            self._tokenizer = None

    def _unload_components(self) -> None:
        """Unload all components in sequence.

        Calls all unload methods in proper order: workflow manager,
        tool manager, chat model, tokenizer, and model.
        """
        for unload_func in [
            self._unload_workflow_manager,
            self._unload_tool_manager,
            self._unload_chat_model,
            self._unload_tokenizer,
            self._unload_model,
        ]:
            try:
                unload_func()
            except Exception as e:
                self.logger.error(f"Error during unload: {e}", exc_info=True)
