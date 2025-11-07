"""
Batch Request Manager for LLM Generation.

Handles batching and parallel processing of LLM requests to improve
throughput for eval testing and high-load scenarios.
"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass, field
from queue import Queue, Empty
from typing import Dict, Any, Optional, Callable, List
from uuid import uuid4

from airunner.settings import AIRUNNER_LOG_LEVEL
from airunner.utils.application import get_logger


@dataclass
class BatchRequest:
    """Represents a single LLM generation request in a batch.

    Attributes:
        request_id: Unique identifier for this request
        prompt: The prompt text to generate from
        params: Additional generation parameters
        callback: Optional callback function for the response
        future: Future object for async result retrieval
        timestamp: When the request was created
        context: Optional context data for the request
    """

    request_id: str
    prompt: str
    params: Dict[str, Any] = field(default_factory=dict)
    callback: Optional[Callable[[Dict[str, Any]], None]] = None
    future: Optional[Future] = None
    timestamp: float = field(default_factory=time.time)
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BatchResponse:
    """Response for a batch request.

    Attributes:
        request_id: ID of the original request
        text: Generated text
        success: Whether generation succeeded
        error: Error message if failed
        metadata: Additional response metadata
        duration: Time taken to generate
    """

    request_id: str
    text: str = ""
    success: bool = True
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    duration: float = 0.0


class BatchRequestManager:
    """Manages batched LLM generation requests.

    This manager:
    - Queues incoming requests
    - Batches them for efficient processing
    - Processes batches in parallel (for API-based models)
    - Handles response delivery via callbacks/futures

    Args:
        max_batch_size: Maximum number of requests per batch
        batch_timeout: Max time to wait for batch to fill (seconds)
        max_workers: Maximum parallel workers for processing
        enable_batching: Whether to batch requests or process individually
    """

    def __init__(
        self,
        max_batch_size: int = 10,
        batch_timeout: float = 0.1,
        max_workers: int = 4,
        enable_batching: bool = True,
    ):
        """Initialize the batch request manager."""
        self.max_batch_size = max_batch_size
        self.batch_timeout = batch_timeout
        self.max_workers = max_workers
        self.enable_batching = enable_batching

        self.logger = get_logger(__name__, AIRUNNER_LOG_LEVEL)
        self.request_queue: Queue[BatchRequest] = Queue()
        self.active_requests: Dict[str, BatchRequest] = {}
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

        self._running = False
        self._batch_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    def start(self) -> None:
        """Start the batch processing thread."""
        if self._running:
            self.logger.warning("Batch manager already running")
            return

        self._running = True
        self._batch_thread = threading.Thread(
            target=self._batch_processing_loop,
            daemon=True,
        )
        self._batch_thread.start()
        self.logger.info(
            f"Batch request manager started "
            f"(batching={'enabled' if self.enable_batching else 'disabled'})"
        )

    def stop(self) -> None:
        """Stop the batch processing thread."""
        self._running = False
        if self._batch_thread:
            self._batch_thread.join(timeout=5)
        self.executor.shutdown(wait=True)
        self.logger.info("Batch request manager stopped")

    def submit_request(
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
        """
        request_id = str(uuid4())
        future: Future[BatchResponse] = Future()

        request = BatchRequest(
            request_id=request_id,
            prompt=prompt,
            params=params or {},
            callback=callback,
            future=future,
            context=context or {},
        )

        with self._lock:
            self.active_requests[request_id] = request

        self.request_queue.put(request)
        self.logger.debug(f"Submitted request {request_id}")

        return future

    def _batch_processing_loop(self) -> None:
        """Main loop that collects and processes batches."""
        while self._running:
            try:
                batch = self._collect_batch()
                if batch:
                    self._process_batch(batch)
            except Exception as e:
                self.logger.error(f"Error in batch processing loop: {e}")
                time.sleep(0.1)

    def _collect_batch(self) -> List[BatchRequest]:
        """Collect requests into a batch.

        Returns:
            List of requests forming a batch
        """
        batch: List[BatchRequest] = []
        batch_start = time.time()

        while len(batch) < self.max_batch_size:
            timeout = self.batch_timeout - (time.time() - batch_start)
            if timeout <= 0:
                break

            try:
                request = self.request_queue.get(timeout=timeout)
                batch.append(request)

                # If batching disabled, process immediately
                if not self.enable_batching:
                    break

            except Empty:
                break

        return batch

    def _process_batch(self, batch: List[BatchRequest]) -> None:
        """Process a batch of requests.

        For API-based models, requests can be processed in parallel.
        For local models, they're processed sequentially.

        Args:
            batch: List of requests to process
        """
        if len(batch) == 0:
            return

        self.logger.debug(f"Processing batch of {len(batch)} requests")

        # Submit each request to the executor
        futures = []
        for request in batch:
            future = self.executor.submit(
                self._process_single_request,
                request,
            )
            futures.append((request, future))

        # Wait for all to complete and handle responses
        for request, future in futures:
            try:
                response = future.result()
                self._deliver_response(request, response)
            except Exception as e:
                self.logger.error(
                    f"Error processing request {request.request_id}: {e}"
                )
                error_response = BatchResponse(
                    request_id=request.request_id,
                    success=False,
                    error=str(e),
                )
                self._deliver_response(request, error_response)

    def _process_single_request(
        self,
        request: BatchRequest,
    ) -> BatchResponse:
        """Process a single request (to be overridden by subclass).

        This method should be overridden by a subclass or set via
        a processor callback to actually perform the LLM generation.

        Args:
            request: The request to process

        Returns:
            BatchResponse with the result
        """
        # Placeholder - should be overridden
        start_time = time.time()

        # This will be replaced with actual LLM generation
        response = BatchResponse(
            request_id=request.request_id,
            text=f"Processed: {request.prompt[:50]}...",
            success=True,
            duration=time.time() - start_time,
        )

        return response

    def _deliver_response(
        self,
        request: BatchRequest,
        response: BatchResponse,
    ) -> None:
        """Deliver response via callback and/or future.

        Args:
            request: The original request
            response: The response to deliver
        """
        # Set the future result
        if request.future and not request.future.done():
            request.future.set_result(response)

        # Call the callback if provided
        if request.callback:
            try:
                request.callback(response)
            except Exception as e:
                self.logger.error(f"Error in callback: {e}")

        # Remove from active requests
        with self._lock:
            self.active_requests.pop(request.request_id, None)

    def get_active_count(self) -> int:
        """Get number of active requests.

        Returns:
            Number of requests being processed
        """
        with self._lock:
            return len(self.active_requests)

    def wait_for_completion(self, timeout: Optional[float] = None) -> bool:
        """Wait for all active requests to complete.

        Args:
            timeout: Maximum time to wait in seconds

        Returns:
            True if all completed, False if timeout
        """
        start_time = time.time()

        while self.get_active_count() > 0:
            if timeout and (time.time() - start_time) > timeout:
                return False
            time.sleep(0.1)

        return True
