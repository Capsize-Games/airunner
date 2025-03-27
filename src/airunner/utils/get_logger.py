import logging


def get_logger(name: str, level):
    # Configure the logger
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Remove all existing handlers
    if logger.hasHandlers():
        logger.handlers.clear()

    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s - %(funcName)s - %(lineno)d - %(message)s'))
    logger.addHandler(handler)

    # Disable propagation to the root logger
    logger.propagate = False
    return logger