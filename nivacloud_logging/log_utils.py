import functools
import logging
import sys
import threading
from logging import StreamHandler, Formatter

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


# From Python docs via jsonlogger.py:
# http://docs.python.org/library/logging.html#logrecord-attributes
RESERVED_ATTRS = (
    'args', 'asctime', 'created', 'exc_info', 'exc_text', 'filename',
    'funcName', 'levelname', 'levelno', 'lineno', 'module',
    'msecs', 'message', 'msg', 'name', 'pathname', 'process',
    'processName', 'relativeCreated', 'stack_info', 'thread', 'threadName')


class PlaintextLogContextHandler(StreamHandler):
    def handle(self, record):
        ctx = {k: v for (k, v) in LogContext.getcontext().items() if not hasattr(record, k)}

        for key, value in record.__dict__.items():
            if key not in RESERVED_ATTRS and not key.startswith("_") and key != 'context':
                ctx[key] = value

        formatted_ctx = [f"{k}={repr(v)}" for (k, v) in ctx.items()]
        record.context = (" [context: " + ", ".join(formatted_ctx) + "]") if ctx else ""
        return super().handle(record)


def setup_structured_logging(min_level=logging.INFO, stream=None):
    formatter = StackdriverJsonFormatter(timestamp=True)

    # This is a work-around to be able to run tests with pytest's output
    # capture when threading. (It doesn't work when you set it as a
    # default value on the parameter directly, because then it will refer
    # to the actual sys.stdout instead of the captured stdout that it will
    # be bound to within the function. Also using sys.stderr when testing
    # doesn't really work due to how captured output is handled by pytest.)
    if stream is None:
        stream = sys.stdout

    # min_level to info goes to stdout
    stream_handler = StructuredLogContextHandler(stream)
    stream_handler.setLevel(min_level)
    stream_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.addHandler(stream_handler)
    root_logger.setLevel(min_level)

    sys.excepthook = global_exception_handler


def setup_plaintext_logging(min_level=logging.INFO, stream=None):
    formatter = Formatter(fmt="%(asctime)s %(levelname)-7s "
                              "%(filename)s:%(lineno)s:%(funcName)s, "
                              "pid=%(process)d, thread=%(thread)d: %(message)s%(context)s")

    # Work-around, see setup_structured_logging:
    if stream is None:
        stream = sys.stderr

    stream_handler = PlaintextLogContextHandler(stream)
    stream_handler.setLevel(min_level)
    stream_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.addHandler(stream_handler)
    root_logger.setLevel(min_level)
