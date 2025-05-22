class BaseTracker:
    """
    Trackers allow you to filter and track arbitrary data based on log entries.
    """

    def process_log_record(self, log_entry):
        """
        Process log record to filter and track data.

        :param log_entry: Log entry to process.
        """
        raise NotImplementedError
