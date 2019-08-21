import functools
import logging

import flask

from nivacloud_logging.log_utils import LogContext


def trace(func):
    """
    A decorator for Flask handlers that takes the Trace-Id header from
    incoming HTTP headers and sets the "trace_id" LogContext to the value
    of this header.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        trace_ctx = {'trace_id': flask.request.headers.get('Trace-Id')}
        with LogContext(**trace_ctx):
            # TODO: Don't do this. Figure out how to inject it into the access log instead...
            logging.info('Traced', extra=trace_ctx)
            return func(*args, **kwargs)

    return wrapper
