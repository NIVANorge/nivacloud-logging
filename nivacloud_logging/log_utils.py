import logging
import os
import sys
import threading
from logging import StreamHandler

from pythonjsonlogger import jsonlogger


class StackdriverJsonFormatter(jsonlogger.JsonFormatter, object):
    """
    Creates a json formatter which outputs logs in a "stackdriver friendly format".
    Following the appraoch described at
    https://medium.com/retailmenot-engineering/formatting-python-logs-for-stackdriver-5a5ddd80761c
    """

    def __init__(self, fmt="%(levelname) %(message) %(filename) %(lineno)", style='%', *args, **kwargs):
        jsonlogger.JsonFormatter.__init__(self, fmt=fmt, *args, **kwargs)

    def process_log_record(self, log_record):
        log_record['severity'] = log_record['levelname']
        log_record["thread"] = threading.get_ident()
        log_record["pid"] = os.getpid()
        del log_record['levelname']
        return super(StackdriverJsonFormatter, self).process_log_record(log_record)


def global_exception_handler(exc_type, value, traceback):
    """
    Intended used as a monkeypatch of sys.excepthook in order to log exceptions.

    Taken from https://stackoverflow.com/questions/6234405/logging-uncaught-exceptions-in-python
    """
    logging.exception(f"Uncaught exception {exc_type.__name__}: {value}", exc_info=(exc_type, value, traceback))


def setup_structured_logging(min_level=logging.INFO):
    formatter = StackdriverJsonFormatter(timestamp=True)

    # min_level to info goes to stdout
    stdout_handler = StreamHandler(sys.stdout)
    stdout_handler.setLevel(min_level)
    stdout_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.addHandler(stdout_handler)
    root_logger.setLevel(min_level)

    sys.excepthook = global_exception_handler
