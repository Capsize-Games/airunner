from PySide6.QtCore import QThread, Signal
import traceback
import time

class BackgroundWorker(QThread):
    """
    A versatile background worker thread for expensive operations.
    
    This class can be used to run any operation in a background thread to prevent
    UI freezing. It provides signals for task completion, progress updates, and error handling.
    """
    # Define signals
    taskFinished = Signal(dict)
    progressUpdate = Signal(int)
    statusUpdate = Signal(str)
    
    def __init__(self, task_function=None, callback_data=None, progress_callback=None):
        """
        Initialize the background worker thread.
        
        Args:
            task_function: The function to execute in the background thread
            callback_data: Optional data to pass back with the finished signal
            progress_callback: Optional function to call to update progress
        """
        super().__init__()
        self.task_function = task_function
        self.callback_data = callback_data or {}
        self.progress_callback = progress_callback
        self._is_cancelled = False
        self._start_time = None
        
    def cancel(self):
        """Request cancellation of the running task"""
        self._is_cancelled = True
        
    @property
    def is_cancelled(self):
        """Check if the task has been requested to cancel"""
        return self._is_cancelled
    
    def update_progress(self, progress_value):
        """Update the progress of the current task (0-100)"""
        self.progressUpdate.emit(progress_value)
        
    def update_status(self, status_message):
        """Update the status message of the current task"""
        self.statusUpdate.emit(status_message)
        
    def run(self):
        """Execute the task function in a separate thread"""
        self._start_time = time.time()
        try:
            # If we have a task function, call it
            if self.task_function:
                # Add the worker instance to the callback data so the task can
                # access methods like update_progress and is_cancelled
                self.task_function_args = {
                    'worker': self
                }
                
                result = self.task_function(**self.task_function_args)
                
                # If the function returned a result, add it to callback data
                if result is not None:
                    self.callback_data['result'] = result
                    
            # Calculate task duration
            duration = time.time() - self._start_time
            self.callback_data['duration'] = duration
            self.callback_data['cancelled'] = self._is_cancelled
                    
            # Signal completion with the callback data
            self.taskFinished.emit(self.callback_data)
        except Exception as e:
            # Add error information to callback data
            self.callback_data['error'] = str(e)
            self.callback_data['error_traceback'] = traceback.format_exc()
            self.callback_data['duration'] = time.time() - self._start_time
            self.callback_data['cancelled'] = self._is_cancelled
            self.taskFinished.emit(self.callback_data)