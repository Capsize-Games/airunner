import traceback


class LogDiscWriter:
    """
    Logs all writing attempts to the disk

    """

    def __init__(self):
        self.total_write_attempts = 0

    def __call__(self, *args, **kwargs):
        self.total_write_attempts += 1
        print(f"Write attempt: {self.total_write_attempts}")

        # show where write came from:
        filename = kwargs.get("filename", None)
        if not filename:
            stack = traceback.extract_stack()
            filename = stack[-2].filename
        print(f"Write attempt from: {filename}")
