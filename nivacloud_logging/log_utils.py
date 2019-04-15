import functools
import logging
import os
import sys
import threading
from logging import StreamHandler, Formatter

from nivacloud_logging.json_formatter import StackdriverJsonFormatter


class LogContext:
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
        self.previous_values = {}

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
        for ctx_key, ctx_value in self.context_values.items():
            self.previous_values[ctx_key] = getattr(self.__context, ctx_key, None)
            setattr(self.__context, ctx_key, ctx_value)

    def _exit_context(self):
        for ctx_key in self.context_values.keys():
            previous = self.previous_values[ctx_key]
            if previous is None:
                delattr(self.__context, ctx_key)
            else:
                setattr(self.__context, ctx_key, previous)

    @classmethod
    def getcontext(cls):
        return cls.__context.__dict__.copy()


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


def _global_exception_handler(exc_type, value, traceback):
    """
    Intended used as a monkeypatch of sys.excepthook in order to log exceptions.

    Taken from https://stackoverflow.com/questions/6234405/logging-uncaught-exceptions-in-python
    """
    logging.exception(f"Uncaught exception {exc_type.__name__}: {value}", exc_info=(exc_type, value, traceback))


class _LogContextHandler(StreamHandler):
    pass


class _StructuredLogContextHandler(_LogContextHandler):
    def handle(self, record):
        for (k, v) in LogContext.getcontext().items():
            if not hasattr(record, k):
                setattr(record, k, v)

        return super().handle(record)


class _PlaintextLogContextHandler(_LogContextHandler):
    # From Python docs via jsonlogger.py:
    # http://docs.python.org/library/logging.html#logrecord-attributes
    RESERVED_ATTRS = {
        'args', 'asctime', 'created', 'exc_info', 'exc_text', 'filename',
        'funcName', 'levelname', 'levelno', 'lineno', 'module',
        'msecs', 'message', 'msg', 'name', 'pathname', 'process',
        'processName', 'relativeCreated', 'stack_info', 'thread', 'threadName'}

    def handle(self, record):
        ctx = {k: v for (k, v) in LogContext.getcontext().items() if not hasattr(record, k)}

        for key, value in record.__dict__.items():
            if key not in self.RESERVED_ATTRS and not key.startswith("_") and key != 'context':
                ctx[key] = value

        formatted_ctx = [f"{k}={repr(v)}" for (k, v) in ctx.items()]
        record.context = (" [context: " + ", ".join(formatted_ctx) + "]") if ctx else ""
        return super().handle(record)


def _remove_existing_stream_handlers():
    """
    Remove existing root logger handlers so that we can safely re-run log setup.
    """
    root_logger = logging.root
    for handler in root_logger.handlers:
        if isinstance(handler, _LogContextHandler):
            root_logger.removeHandler(handler)


def _setup_structured_logging(min_level, stream):
    formatter = StackdriverJsonFormatter(timestamp=True)

    stream_handler = _StructuredLogContextHandler(stream)
    stream_handler.setLevel(min_level)
    stream_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    _remove_existing_stream_handlers()
    root_logger.addHandler(stream_handler)
    root_logger.setLevel(min_level)

    sys.excepthook = _global_exception_handler


def _setup_plaintext_logging(min_level, stream):
    formatter = Formatter(fmt="%(asctime)s %(levelname)-7s "
                              "%(filename)s:%(lineno)s:%(funcName)s, "
                              "pid=%(process)d, thread=%(thread)d: %(message)s%(context)s")

    stream_handler = _PlaintextLogContextHandler(stream)
    stream_handler.setLevel(min_level)
    stream_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    _remove_existing_stream_handlers()
    root_logger.addHandler(stream_handler)
    root_logger.setLevel(min_level)


def _override_log_handlers():
    loggers = logging.root.manager.loggerDict.values()
    for logger in loggers:
        logger.propagate = True
        if hasattr(logger, 'handlers'):
            for handler in logger.handlers:
                logger.removeHandler(handler)
        logger.propagate = True


def setup_logging(min_level=logging.INFO, plaintext=None, stream=None, override=None):
    """
    Set up logging with sensible defaults. Enables output of structured
    log contexts using the LogContext context manager.

    :param min_level: Minimal log level to output at.
    :param plaintext: If True, output human-readable logs, otherwise output
        JSON suitable for Stackdriver. If None, use plaintext logging if
        the NIVACLOUD_PLAINTEXT_LOGS environment variable is set.
    :param stream: If None, default to sys.stdout for structured logs
        or sys.stderr for plaintext output.
    :param override: If true (default), remove all handlers except the ones
        on the root logger and enable propagation for every logger. To make
        sure that we receive all the log entries in the format we want with '
        contexts. Can be enabled/disabled with NIVACLOUD_OVERRIDE_LOGGERS
        environment variable.
    """

    if plaintext is None:
        plaintext = os.getenv('NIVACLOUD_PLAINTEXT_LOGS', '').lower() not in ('', '0', 'false', 'f')

    if override is None:
        override = os.getenv('NIVACLOUD_OVERRIDE_LOGGERS', '1').lower() in ('1', 'true', 't')

    # This is a work-around to be able to run tests with pytest's output
    # capture when threading. (It doesn't work when you set it as a
    # default value on the parameter directly, because then it will refer
    # to the actual sys.stdout instead of the captured stdout that it will
    # be bound to within the function. Also using sys.stderr when testing
    # doesn't really work due to how captured output is handled by pytest.)
    if stream is None:
        stream = sys.stderr if plaintext else sys.stdout

    if plaintext:
        _setup_plaintext_logging(min_level, stream)
    else:
        _setup_structured_logging(min_level, stream)

    if override:
        _override_log_handlers()
