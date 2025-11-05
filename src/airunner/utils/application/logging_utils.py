import functools
import logging


def log_method_entry_exit(method):
    """
    Decorator to log entry and exit of a method using the instance's logger if available.
    Logs exit even if an exception is raised.
    """

    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        logger = getattr(self, "logger", None)
        method_name = method.__qualname__
        if logger:
            logger.debug(f"Entering {method_name}")
        else:
            logging.debug(f"Entering {method_name}")
        try:
            result = method(self, *args, **kwargs)
        except Exception:
            if logger:
                logger.debug(f"Exiting {method_name}")
            else:
                logging.debug(f"Exiting {method_name}")
            raise
        if logger:
            logger.debug(f"Exiting {method_name}")
        else:
            logging.debug(f"Exiting {method_name}")
        return result

    return wrapper
