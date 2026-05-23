"""Service-owned application exception types."""


class PipeNotLoadedException(Exception):
	"""Raised when a required art pipeline has not been loaded yet."""

	def __init__(self, message="Pipe not loaded"):
		self.message = message
		super().__init__(self.message)


class SafetyCheckerNotLoadedException(Exception):
	"""Raised when the configured safety checker is unavailable."""

	def __init__(self, message="Safety checker not ready"):
		self.message = message
		super().__init__(self.message)


class InterruptedException(Exception):
	"""Raised when work is intentionally interrupted."""

	def __init__(self, message="Interrupted"):
		self.message = message
		super().__init__(self.message)


class AutoExportSeedException(Exception):
	"""Raised when auto export is requested without a stable seed."""

	def __init__(
		self, message="Seed must be set when auto exporting an image"
	):
		self.message = message
		super().__init__(self.message)


class PythonExecutableNotFoundException(Exception):
	"""Raised when a configured Python executable cannot be located."""

	def __init__(self, message="Could not find python executable in venv"):
		self.message = message
		super().__init__(self.message)


class PromptTemplateNotFoundExeption(Exception):
	"""Raised when a referenced prompt template cannot be found."""

	def __init__(self, message="Prompt template not found"):
		self.message = message
		super().__init__(self.message)


class ThreadInterruptException(Exception):
	"""Raised to stop background worker threads."""


class NaNException(Exception):
	"""Raised when NaN values are detected in generated data."""

	def __init__(self, message="NaN values found"):
		self.message = message
		super().__init__(self.message)