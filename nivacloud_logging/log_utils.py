import functools
import logging
import sys
import threading
from logging import StreamHandler

from nivacloud_logging.json_formatter import StackdriverJsonFormatter


class LogContext(object):
    """
    Establish a (synchronous or asynchronous) logging context with the given
    context_values. This context manager is reentrant, so you can have nested context.

    Sample usage:

        with LogContext(trace_id=123):
            logging.error("Something really bad happened!")
    """

    __context = threading.local()

    def __init__(self, **context_values):
        self.context_values = context_values

    async def __aenter__(self):
        self._enter_context()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self._exit_context()

    def __enter__(self):
        self._enter_context()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._exit_context()

    def _enter_context(self):
        for (ctx_key, ctx_value) in self.context_values.items():
            stack = getattr(self.__context, ctx_key, [])
            setattr(self.__context, ctx_key, stack)
            stack.append(ctx_value)

    def _exit_context(self):
        for ctx_key in self.context_values.keys():
            stack = getattr(self.__context, ctx_key, None)
            if stack:
                stack.pop()

    @classmethod
    def getcontext(cls):
        return {k: v[-1] for (k, v) in cls.__context.__dict__.items() if v}


def log_context(**ctxargs):
    """
    A decorator that wraps a function using the LogContext class.

    Sample usage:
        @log_context(foo="bar")
        def xyzzy(x):
            logging.info("I'll also log something about foo.")
    """

    def metawrap(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with LogContext(**ctxargs):
                return func(*args, **kwargs)

        return wrapper

    return metawrap


def global_exception_handler(exc_type, value, traceback):
    """
    Intended used as a monkeypatch of sys.excepthook in order to log exceptions.

    Taken from https://stackoverflow.com/questions/6234405/logging-uncaught-exceptions-in-python
    """
    logging.exception(f"Uncaught exception {exc_type.__name__}: {value}", exc_info=(exc_type, value, traceback))


class StructuredLogContextHandler(StreamHandler):
    def handle(self, record):
        for (k, v) in LogContext.getcontext().items():
            if not hasattr(record, k):
                setattr(record, k, v)

        return super().handle(record)


def setup_structured_logging(min_level=logging.INFO):
    formatter = StackdriverJsonFormatter(timestamp=True)

    # min_level to info goes to stdout
    stdout_handler = StructuredLogContextHandler(sys.stdout)
    stdout_handler.setLevel(min_level)
    stdout_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.addHandler(stdout_handler)
    root_logger.setLevel(min_level)

    sys.excepthook = global_exception_handler
