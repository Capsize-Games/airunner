from typing import Dict, Any, Optional, Callable

from airunner.utils.application.background_worker import BackgroundWorker


class ThreadedWorkerMixin:
    """
    A mixin that adds background thread capabilities to worker classes.
    
    This mixin provides standardized methods for executing CPU/GPU intensive
    operations in background threads to prevent UI freezing.
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize the mixin and set up thread tracking"""
        # Dictionary to store active background workers
        self._background_workers = {}
        
        # Call super init if this is used as a mixin
        super().__init__(*args, **kwargs)
        
    def execute_in_background(
        self,
        task_function: Callable,
        task_id: str = "default",
        callback_data: Dict[str, Any] = None,
        on_finished: Callable = None,
        on_progress: Callable = None,
        on_status: Callable = None
    ) -> None:
        """
        Execute a function in a background thread.
        
        Args:
            task_function: The function to execute in the background
            task_id: Unique identifier for this task (used to cancel specific tasks)
            callback_data: Data to include with the completion callback
            on_finished: Function to call when the task is finished
            on_progress: Function to call when progress is updated
            on_status: Function to call when status is updated
        """
        # Stop existing worker with the same ID if it exists
        self.stop_background_task(task_id)
        
        # Create a new background worker
        worker = BackgroundWorker(
            task_function=task_function,
            callback_data=callback_data or {}
        )
        
        # Store in the worker dictionary
        self._background_workers[task_id] = worker
        
        # Connect signals
        if on_finished:
            worker.taskFinished.connect(
                lambda data: self._handle_task_finished(task_id, data, on_finished)
            )
        else:
            worker.taskFinished.connect(
                lambda data: self._cleanup_worker(task_id)
            )
            
        if on_progress:
            worker.progressUpdate.connect(on_progress)
            
        if on_status:
            worker.statusUpdate.connect(on_status)
            
        # Start the worker
        worker.start()
        
        # Return the worker ID for reference
        return task_id
    
    def _handle_task_finished(self, task_id: str, data: Dict[str, Any], callback: Callable) -> None:
        """Handle task completion, cleanup, and invoke callback"""
        # Clean up the worker
        self._cleanup_worker(task_id)
        
        # Call the provided callback
        if callback:
            callback(data)
    
    def _cleanup_worker(self, task_id: str) -> None:
        """Remove a worker from the tracking dictionary"""
        if task_id in self._background_workers:
            # Wait for the worker to finish if it's not already done
            worker = self._background_workers[task_id]
            if worker.isRunning():
                worker.wait()
            
            # Delete the worker
            del self._background_workers[task_id]
    
    def stop_background_task(self, task_id: str) -> None:
        """Stop a specific background task if it's running"""
        if task_id in self._background_workers:
            worker = self._background_workers[task_id]
            if worker.isRunning():
                worker.cancel()
                worker.wait()
            self._cleanup_worker(task_id)
    
    def stop_all_background_tasks(self) -> None:
        """Stop all running background tasks"""
        for task_id in list(self._background_workers.keys()):
            self.stop_background_task(task_id)
            
    def get_active_background_tasks(self) -> list:
        """Return a list of active task IDs"""
        return list(self._background_workers.keys())