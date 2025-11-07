"""
Batch Processing Mixin for LLM Model Manager.

Provides batched and parallel request processing capabilities.
"""

from typing import Dict, Any, Optional, Callable
from concurrent.futures import Future

from airunner.components.llm.managers.batch_request_manager import (
    BatchRequestManager,
    BatchRequest,
    BatchResponse,
)
from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger


class BatchProcessingMixin:
    """Mixin to add batch processing capabilities to LLMModelManager.

    This mixin provides:
    - Batch request submission
    - Parallel processing for API-based models
    - Async response delivery
    - Backwards compatible with single-request interface
    """

    def __init__(self, *args, **kwargs):
        """Initialize batch processing components."""
        super().__init__(*args, **kwargs)
        self._batch_manager: Optional[BatchRequestManager] = None
        self._batch_enabled = False
        self.logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)

    def enable_batch_processing(
        self,
        max_batch_size: int = 10,
        batch_timeout: float = 0.1,
        max_workers: int = 4,
    ) -> None:
        """Enable batch processing mode.

        Args:
            max_batch_size: Maximum requests per batch
            batch_timeout: Max wait time for batch to fill
            max_workers: Maximum parallel workers
        """
        if self._batch_manager is not None:
            self.logger.warning("Batch processing already enabled")
            return

        self._batch_manager = BatchRequestManager(
            max_batch_size=max_batch_size,
            batch_timeout=batch_timeout,
            max_workers=max_workers,
            enable_batching=self._should_enable_batching(),
        )

        # Override the processing method
        self._batch_manager._process_single_request = (
            self._process_batch_request
        )

        self._batch_manager.start()
        self._batch_enabled = True

        self.logger.info(
            f"Batch processing enabled "
            f"(batching={self._should_enable_batching()})"
        )

    def disable_batch_processing(self) -> None:
        """Disable batch processing mode."""
        if self._batch_manager:
            self._batch_manager.stop()
            self._batch_manager = None
        self._batch_enabled = False
        self.logger.info("Batch processing disabled")

    def _should_enable_batching(self) -> bool:
        """Determine if batching should be enabled.

        Batching is beneficial for API-based models (OpenRouter, Ollama)
        where requests can be processed in parallel. For local models,
        we still use the manager but with batching disabled (sequential).

        Returns:
            True if batching should be enabled
        """
        # Check if using API-based model service
        if hasattr(self, "llm_settings"):
            use_openrouter = getattr(
                self.llm_settings, "use_openrouter", False
            )
            use_ollama = getattr(self.llm_settings, "use_ollama", False)
            return use_openrouter or use_ollama
        return False

    def submit_batch_request(
        self,
        prompt: str,
        params: Optional[Dict[str, Any]] = None,
        callback: Optional[Callable[[BatchResponse], None]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Future[BatchResponse]:
        """Submit a request for batched processing.

        Args:
            prompt: The prompt text
            params: Generation parameters
            callback: Optional callback for response
            context: Optional context data

        Returns:
            Future that will contain the BatchResponse

        Raises:
            RuntimeError: If batch processing not enabled
        """
        if not self._batch_enabled or self._batch_manager is None:
            raise RuntimeError(
                "Batch processing not enabled. "
                "Call enable_batch_processing() first."
            )

        return self._batch_manager.submit_request(
            prompt=prompt,
            params=params,
            callback=callback,
            context=context,
        )

    def _process_batch_request(
        self,
        request: BatchRequest,
    ) -> BatchResponse:
        """Process a single request from the batch.

        This method integrates with the existing handle_request logic
        but adapts it for batch processing.

        Args:
            request: The request to process

        Returns:
            BatchResponse with the result
        """
        import time

        start_time = time.time()

        try:
            # Build message dict compatible with existing handle_request
            message = {
                "prompt": request.prompt,
                **request.params,
                **request.context,
            }

            # Use existing generation logic
            # We need to capture the response instead of using signals
            response_text = self._generate_batch_response(message)

            return BatchResponse(
                request_id=request.request_id,
                text=response_text,
                success=True,
                duration=time.time() - start_time,
            )

        except Exception as e:
            self.logger.error(f"Batch request failed: {e}")
            return BatchResponse(
                request_id=request.request_id,
                success=False,
                error=str(e),
                duration=time.time() - start_time,
            )

    def _generate_batch_response(self, message: Dict[str, Any]) -> str:
        """Generate response for batch request.

        This method should call the appropriate generation logic
        based on the model type (local, OpenRouter, Ollama).

        Args:
            message: Request message dictionary

        Returns:
            Generated text
        """
        # This will be implemented to call the appropriate
        # generation method based on model service

        # For OpenRouter/Ollama, we can use the ChatModel directly
        if hasattr(self, "llm_settings"):
            if getattr(self.llm_settings, "use_openrouter", False):
                return self._generate_openrouter_batch(message)
            elif getattr(self.llm_settings, "use_ollama", False):
                return self._generate_ollama_batch(message)

        # For local models, use existing generation
        return self._generate_local_batch(message)

    def _generate_openrouter_batch(self, message: Dict[str, Any]) -> str:
        """Generate using OpenRouter (for batch processing).

        Args:
            message: Request message

        Returns:
            Generated text
        """
        # Use existing ChatModel
        if hasattr(self, "chat_model") and self.chat_model:
            response = self.chat_model.invoke(message.get("prompt", ""))
            return (
                response.content
                if hasattr(response, "content")
                else str(response)
            )

        raise RuntimeError("ChatModel not initialized for OpenRouter")

    def _generate_ollama_batch(self, message: Dict[str, Any]) -> str:
        """Generate using Ollama (for batch processing).

        Args:
            message: Request message

        Returns:
            Generated text
        """
        # Use existing ChatModel
        if hasattr(self, "chat_model") and self.chat_model:
            response = self.chat_model.invoke(message.get("prompt", ""))
            return (
                response.content
                if hasattr(response, "content")
                else str(response)
            )

        raise RuntimeError("ChatModel not initialized for Ollama")

    def _generate_local_batch(self, message: Dict[str, Any]) -> str:
        """Generate using local model (for batch processing).

        Args:
            message: Request message

        Returns:
            Generated text
        """
        # For local models, we need to use the existing generation
        # pipeline but capture the output synchronously

        # This is a simplified version - actual implementation
        # would integrate with the existing generation logic
        raise NotImplementedError(
            "Local model batch processing requires "
            "integration with existing generation pipeline"
        )

    def wait_for_batch_completion(
        self, timeout: Optional[float] = None
    ) -> bool:
        """Wait for all batch requests to complete.

        Args:
            timeout: Maximum time to wait

        Returns:
            True if completed, False if timeout
        """
        if not self._batch_enabled or self._batch_manager is None:
            return True

        return self._batch_manager.wait_for_completion(timeout)

    def get_batch_active_count(self) -> int:
        """Get number of active batch requests.

        Returns:
            Number of requests being processed
        """
        if not self._batch_enabled or self._batch_manager is None:
            return 0

        return self._batch_manager.get_active_count()
