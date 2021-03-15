import logging
import time

from nivacloud_logging.log_utils import LogContext, generate_trace_id


class TracingMiddleware:
    """
    WSGI middleware that looks for a Trace-Id header in every request and adds it to
    LogContext for that request if found.

    Usage:
      app = Flask(__name__)
      app.wsgi_app = TracingMiddleware(app.wsgi_app)
    """

    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        def execute_traced_request():
            t0 = time.monotonic()
            r = self.app(environ, start_response)
            elapsed = time.monotonic() - t0
            logging.info(
                f"{environ.get('REQUEST_METHOD')} {environ.get('RAW_URI')} "
                f"{environ.get('SERVER_PROTOCOL')} from {environ.get('REMOTE_ADDR')}",
                extra={
                    "elapsed_s": elapsed,
                    "raw_uri": environ.get("RAW_URI"),
                    "remote_addr": environ.get("REMOTE_ADDR"),
                    "server_protocol": environ.get("SERVER_PROTOCOL"),
                },
            )
            return r

        contextvars = {
            "trace_id": environ.get("HTTP_TRACE_ID"),
            "user_id": environ.get("HTTP_USER_ID"),
            "span_id": environ.get("HTTP_SPAN_ID") or generate_trace_id(),
        }

        contextvars_with_values = {
            k: v for k, v in contextvars.items() if v is not None
        }

        with LogContext(**contextvars_with_values):
            return execute_traced_request()
