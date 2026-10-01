import logging

def get_logger(name: str = __file__, level: str = "INFO"):
    # Configure structured logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s"
    )
    logger = logging.getLogger(name=name)
    logger.setLevel(level=level)
    return logger