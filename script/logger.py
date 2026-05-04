import logging
import os 

LOG_LEVEL =os.getenv("LOG_LEVEL", "INFO")

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"

def setup_logging():
    logging.basicConfig(
        level=LOG_LEVEL,
        format=LOG_FORMAT
    )
def get_logger(name: str):
    return logging.getLogger(name)    