import logging
import sys
from config.settings import settings
def get_logger(name :str) -> logging.Logger:
    """
    Creates a configured logger instance enforcing the project's format.

    This logger outputs to stdout with a strictly defined format including
    timestamp, log level, module name, and source file location. It prevents
    log propagation to avoid duplicate entries in the root logger.

    Args:
        name (str): The name of the module requesting the logger (typically __name__).

    Returns:
        logging.Logger: A configured logger instance ready for use.
    """

    logger = logging.getLogger(name)
    logger.setLevel(settings.LOG_LEVEL)

    if not logger.handlers:
        handler =  logging.StreamHandler(sys.stdout)

        formatter = logging.Formatter(
            fmt="[%(asctime)s] [%(levelname)s] [%(name)s] [%(filename)s:%(lineno)d]: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)

        logger.propagate = False

    return logger