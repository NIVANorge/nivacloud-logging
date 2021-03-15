import functools
import inspect
import json
import logging
import os
import random
import signal
import sys
import threading
from datetime import datetime, date, time
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
    __default_context = {}
    __default_context_lock = threading.Lock()

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
    def getcontext(cls, key=None):
        """Returns the thread-local value for given key or a default global value
        if it doesn't exist. Returns the whole context if no key is given."""
        with cls.__default_context_lock:
            if key is None:
                return {**cls.__default_context, **cls.__context.__dict__}
            else:
                return cls.__context.__dict__.get(key, cls.__default_context.get(key))

    @classmethod
    def set_default(cls, key, value):
        """Set global default value for given key. Shared by all threads. These are used
        when no thread-local value is available for given key."""
        with cls.__default_context_lock:
            cls.__default_context[key] = value

    @classmethod
    def reset_defaults(cls):
        with cls.__default_context_lock:
            cls.__default_context = {}


# noinspection PyPep8Naming
class log_exceptions:
    """
    A context manager that logs exceptions. Will by default re-raise, but
    can swallow instead if suppress is set to True.

    Sample usage:
        with LogContext(abc="def"), log_exceptions():
            raise Exception("I'm in your code, raising exceptions!")
    """

    def __init__(self, suppress=False):
        self._suppress = suppress

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            logging.exception(exc_val, exc_info=(exc_type, exc_val, exc_tb))
        return self._suppress


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


def auto_context(*context_args: str):
    """
    Automatically generate a context for the function it wraps consisting of the parameter names
    associated with argument values. Optionally specify the parameters we want to include, otherwise
    all are included.

    Sample usage:
        @auto_context("host", "user")
        def login(host, user, password):
            logging.info("Logging in...")    # Will add only host and user to LogContext

        @auto_context()
        def lookup(host, *servers):
            logging.info("Doing lookup...")  # Will add both host and servers to LogContext

    :param context_args: If provided list the names of parameters that should be included in the log context.
    """

    def meta_wrap(func):
        signature = inspect.signature(func)
        included_args = set(signature.parameters.keys()) - {"self"}
        if context_args:
            included_args &= set(context_args)

        @functools.wraps(func)
        def auto_ctx_wrapper(*args, **kwargs):
            bound_args = signature.bind(*args, **kwargs)
            bound_args.apply_defaults()
            log_params = {
                k: v for (k, v) in bound_args.arguments.items() if k in included_args
            }

            with LogContext(**log_params):
                return func(*args, **kwargs)

        return auto_ctx_wrapper

    return meta_wrap


def generate_trace_id():
    """
    Create a random number formatted as a hexadecimal string, suitable for use
    as a trace identifier.
    """
    return f"{random.randint(0, 2 ** 128 - 1):x}"


def _global_exception_handler(exc_type, value, traceback):
    """
    Intended used as a monkeypatch of sys.excepthook in order to log exceptions.

    Taken from https://stackoverflow.com/questions/6234405/logging-uncaught-exceptions-in-python
    """
    logging.exception(
        f"Uncaught exception {exc_type.__name__}: {value}",
        exc_info=(exc_type, value, traceback),
    )


def _loglevel_signal_handler(loggers):
    """
    Handle SIGUSR1 and SIGUSR2. Sets log level to INFO on SIGUSR1 and DEBUG on SIGUSR2.

    After setting level, it calls the previous SIGUSRx handler unless it was set to SIG_DFL.
    """
    usr_signals = {
        signal.SIGUSR1: logging.INFO,
        signal.SIGUSR2: logging.DEBUG,
    }

    previous_handlers = {
        signalnum: handler
        for (signalnum, handler) in zip(usr_signals, map(signal.getsignal, usr_signals))
        if handler != signal.SIG_DFL
    }

    def handle_usr_signal(signalnum, _frame):
        level = usr_signals[signalnum]
        for logger in loggers:
            logger.setLevel(level)

        previous_handler = previous_handlers.get(signalnum)
        if previous_handler:
            previous_handler(signalnum, _frame)

    signal.signal(signal.SIGUSR1, handle_usr_signal)
    signal.signal(signal.SIGUSR2, handle_usr_signal)


def json_default(o):
    if isinstance(o, (date, datetime, time)):
        return o.isoformat()
    elif isinstance(o, complex):
        return {"real": o.real, "imag": o.imag}
    else:
        return str(o)


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
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "module",
        "msecs",
        "message",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "thread",
        "threadName",
    }

    def handle(self, record):
        ctx = {
            k: v for (k, v) in LogContext.getcontext().items() if not hasattr(record, k)
        }

        for key, value in record.__dict__.items():
            if (
                key not in self.RESERVED_ATTRS
                and not key.startswith("_")
                and key != "context"
            ):
                ctx[key] = value

        formatted_ctx = [f"{k}={self.plain_repr(v)}" for (k, v) in ctx.items()]
        record.context = (" [" + ", ".join(formatted_ctx) + "]") if ctx else ""
        return super().handle(record)

    @staticmethod
    def plain_repr(o):
        return json.dumps(o, default=json_default, sort_keys=True)


def _remove_existing_stream_handlers():
    """
    Remove existing root logger handlers so that we can safely re-run log setup.
    """
    root_logger = logging.root
    for handler in root_logger.handlers:
        if isinstance(handler, _LogContextHandler):
            root_logger.removeHandler(handler)


def _setup_structured_logging(min_level, stream):
    formatter = StackdriverJsonFormatter(timestamp=True, json_default=json_default)

    stream_handler = _StructuredLogContextHandler(stream)
    stream_handler.setLevel(min_level)
    stream_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    _remove_existing_stream_handlers()
    root_logger.addHandler(stream_handler)
    root_logger.setLevel(min_level)

    sys.excepthook = _global_exception_handler

    return [stream_handler, root_logger]


def _setup_plaintext_logging(min_level, stream):
    formatter = Formatter(
        fmt="%(asctime)s %(levelname)-7s "
        "%(filename)s:%(lineno)s:%(funcName)s, "
        "process=%(process)d, thread=%(thread)d: %(message)s%(context)s"
    )

    stream_handler = _PlaintextLogContextHandler(stream)
    stream_handler.setLevel(min_level)
    stream_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    _remove_existing_stream_handlers()
    root_logger.addHandler(stream_handler)
    root_logger.setLevel(min_level)

    return [stream_handler, root_logger]


def _override_log_handlers():
    loggers = logging.root.manager.loggerDict.values()
    for logger in [logging.root, *loggers]:
        if hasattr(logger, "handlers"):
            for handler in logger.handlers[:]:
                if not isinstance(handler, _LogContextHandler):
                    logger.removeHandler(handler)
        logger.propagate = True


def setup_logging(min_level=logging.INFO, plaintext=None, stream=None, override=None):
    """
    Set up logging with sensible defaults. Enables output of structured
    log contexts using the LogContext context manager.

    (Note that the JSON-formatted handler also sets up a global exception handler
    by overriding sys.excepthook.)

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
        plaintext = os.getenv("NIVACLOUD_PLAINTEXT_LOGS", "").lower() not in (
            "",
            "0",
            "false",
            "f",
        )

    if override is None:
        override = os.getenv("NIVACLOUD_OVERRIDE_LOGGERS", "1").lower() in (
            "1",
            "true",
            "t",
        )

    LogContext.reset_defaults()
    commit_id = os.getenv("GIT_COMMIT_ID")
    if commit_id and commit_id != "unknown":
        LogContext.set_default("git_commit_id", commit_id)

    # This is a work-around to be able to run tests with pytest's output
    # capture when threading. (It doesn't work when you set it as a
    # default value on the parameter directly, because then it will refer
    # to the actual sys.stdout instead of the captured stdout that it will
    # be bound to within the function. Also using sys.stderr when testing
    # doesn't really work due to how captured output is handled by pytest.)
    if stream is None:
        stream = sys.stderr if plaintext else sys.stdout

    if plaintext:
        loggers = _setup_plaintext_logging(min_level, stream)
    else:
        loggers = _setup_structured_logging(min_level, stream)

    if override:
        _override_log_handlers()

    _loglevel_signal_handler(loggers)
