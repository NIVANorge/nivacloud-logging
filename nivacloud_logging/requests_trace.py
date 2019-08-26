from requests.adapters import HTTPAdapter

from nivacloud_logging.log_utils import LogContext, generate_trace_id


class TracingAdapter(HTTPAdapter):
    """
    Subclass of HTTPAdapter that adds a Trace-Id header if not already supplied.

    Sample usage:
        session = requests.Session()
        session.mount('http://', TracingAdapter())
        session.mount('https://', TracingAdapter())
        r = session.get("https://httpbin.org/headers")
        print(f"Trace-ID is {r.json()['headers'].get('Trace-Id')}")
    """

    def add_headers(self, request, **kwargs):
        super().add_headers(request, **kwargs)
        incoming_trace_id = LogContext.getcontext("trace_id")
        request.headers['Trace-Id'] = incoming_trace_id or generate_trace_id()
