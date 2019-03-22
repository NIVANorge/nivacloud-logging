import os
import threading

from pythonjsonlogger import jsonlogger


class StackdriverJsonFormatter(jsonlogger.JsonFormatter, object):
    """
    Creates a json formatter which outputs logs in a "stackdriver friendly format".
    Following the appraoch described at
    https://medium.com/retailmenot-engineering/formatting-python-logs-for-stackdriver-5a5ddd80761c

    maps levelname to severity as this is the format used by google stackdriver

    """

    def __init__(self, fmt="%(levelname) %(message) %(filename) %(lineno)", style='%', *args, **kwargs):
        jsonlogger.JsonFormatter.__init__(self, fmt=fmt, *args, **kwargs)

    def process_log_record(self, log_record):
        log_record['severity'] = log_record['levelname']
        log_record["thread"] = threading.get_ident()
        log_record["pid"] = os.getpid()
        del log_record['levelname']
        return super(StackdriverJsonFormatter, self).process_log_record(log_record)
