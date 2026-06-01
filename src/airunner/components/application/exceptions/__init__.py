class InterruptedException(Exception):
    def __init__(self, message="Interrupted"):
        self.message = message
        super().__init__(self.message)


