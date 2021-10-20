import logging


def setup_logging(log_level):
    logger_format = logging.Formatter('[%(asctime)s] [%(levelname)s] - %(message)s')
    logger = logging.getLogger(__name__)
    logger.setLevel(log_level)

    # Write to Stdout
    handler = logging.FileHandler('../logs.log')
    handler.setLevel(log_level)
    handler.setFormatter(logger_format)
    logger.addHandler(handler)

    return logger
