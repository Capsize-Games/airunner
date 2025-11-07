"""Tests for batch request processing."""

from airunner.components.llm.managers.batch_request_manager import (
    BatchRequestManager,
    BatchRequest,
    BatchResponse,
)


class TestBatchRequestManager:
    """Test BatchRequestManager functionality."""

    def test_manager_initialization(self):
        """Test manager can be initialized."""
        manager = BatchRequestManager(
            max_batch_size=5,
            batch_timeout=0.1,
            max_workers=2,
        )
        assert manager.max_batch_size == 5
        assert manager.batch_timeout == 0.1
        assert manager.max_workers == 2

    def test_manager_start_stop(self):
        """Test manager can start and stop."""
        manager = BatchRequestManager()
        manager.start()
        assert manager._running

        manager.stop()
        assert not manager._running

    def test_submit_request_returns_future(self):
        """Test submitting a request returns a future."""
        manager = BatchRequestManager()
        manager.start()

        try:
            future = manager.submit_request(
                prompt="Test prompt",
                params={"temperature": 0.8},
            )
            assert future is not None
            assert manager.get_active_count() > 0
        finally:
            manager.stop()

    def test_batch_collection(self):
        """Test requests are collected into batches."""
        manager = BatchRequestManager(max_batch_size=3, batch_timeout=0.5)
        manager.start()

        try:
            # Submit 5 requests
            futures = []
            for i in range(5):
                future = manager.submit_request(
                    prompt=f"Prompt {i}",
                    params={},
                )
                futures.append(future)

            # Wait for completion
            manager.wait_for_completion(timeout=5)

            # All should complete
            for future in futures:
                assert future.done()
        finally:
            manager.stop()

    def test_custom_processor(self):
        """Test using custom processor function."""
        manager = BatchRequestManager()

        # Override processor to return custom response
        def custom_processor(request: BatchRequest) -> BatchResponse:
            return BatchResponse(
                request_id=request.request_id,
                text=f"Processed: {request.prompt}",
                success=True,
            )

        manager._process_single_request = custom_processor
        manager.start()

        try:
            future = manager.submit_request(prompt="Hello")
            response = future.result(timeout=2)

            assert response.success
            assert "Processed: Hello" in response.text
        finally:
            manager.stop()

    def test_callback_invocation(self):
        """Test callback is called when response ready."""
        manager = BatchRequestManager()
        manager._process_single_request = lambda req: BatchResponse(
            request_id=req.request_id,
            text="Test response",
            success=True,
        )
        manager.start()

        callback_called = []

        def callback(response: BatchResponse):
            callback_called.append(response)

        try:
            future = manager.submit_request(
                prompt="Test",
                callback=callback,
            )
            future.result(timeout=2)

            assert len(callback_called) == 1
            assert callback_called[0].text == "Test response"
        finally:
            manager.stop()

    def test_parallel_processing(self):
        """Test multiple requests processed in parallel."""
        import time

        manager = BatchRequestManager(max_workers=3, enable_batching=True)

        # Slow processor that takes 0.1s per request
        def slow_processor(request: BatchRequest) -> BatchResponse:
            time.sleep(0.1)
            return BatchResponse(
                request_id=request.request_id,
                text=f"Done: {request.prompt}",
                success=True,
            )

        manager._process_single_request = slow_processor
        manager.start()

        try:
            start = time.time()

            # Submit 6 requests
            futures = [
                manager.submit_request(prompt=f"Task {i}") for i in range(6)
            ]

            # Wait for all
            for future in futures:
                future.result(timeout=5)

            duration = time.time() - start

            # With 3 workers, 6 requests should take ~0.2s
            # (2 batches of 3 processed in parallel)
            # Without parallelism, would take 0.6s
            assert duration < 0.4, f"Too slow: {duration:.2f}s"
        finally:
            manager.stop()

    def test_error_handling(self):
        """Test errors are captured in response."""
        manager = BatchRequestManager()

        # Processor that raises exception
        def failing_processor(request: BatchRequest) -> BatchResponse:
            raise RuntimeError("Test error")

        manager._process_single_request = failing_processor
        manager.start()

        try:
            future = manager.submit_request(prompt="Test")
            response = future.result(timeout=2)

            assert not response.success
            assert "Test error" in response.error
        finally:
            manager.stop()
