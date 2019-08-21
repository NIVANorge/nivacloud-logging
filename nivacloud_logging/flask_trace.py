from nivacloud_logging.log_utils import LogContext


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
        trace_id = environ.get('HTTP_TRACE_ID')
        if trace_id:
            with LogContext(trace_id=trace_id):
                return self.app(environ, start_response)
        else:
            return self.app(environ, start_response)
