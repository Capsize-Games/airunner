class PipeNotLoadedException(Exception):
    def __init__(self, message="Pipe not loaded"):
        self.message = message
        super().__init__(self.message)


class SafetyCheckerNotLoadedException(Exception):
    def __init__(self, message="Safety checker not ready"):
        self.message = message
        super().__init__(self.message)


class InterruptedException(Exception):
    def __init__(self, message="Interrupted"):
        self.message = message
        super().__init__(self.message)


class AutoExportSeedException(Exception):
    def __init__(self, message="Seed must be set when auto exporting an image"):
        self.message = message
        super().__init__(self.message)


class PythonExecutableNotFoundException(Exception):
    def __init__(self, message="Could not find python executable in venv"):
        self.message = message
        super().__init__(self.message)


class PromptTemplateNotFoundExeption(Exception):
    def __init__(self, message="Prompt template not found"):
        self.message = message
        super().__init__(self.message)


class ThreadInterruptException(Exception):
    pass


class NaNException(Exception):
    def __init__(self, message="NaN values found"):
        self.message = message
        super().__init__(self.message)
