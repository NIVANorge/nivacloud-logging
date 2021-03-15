from requests.adapters import HTTPAdapter

from nivacloud_logging.log_utils import LogContext, generate_trace_id


class TracingAdapter(HTTPAdapter):
    """
    Subclass of HTTPAdapter that:
     1. Adds Trace-Id if it exists in LogContext.
     2. Adds Span-Id if it exists in LogContext or auto-generates it otherwise.

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
        if incoming_trace_id:
            request.headers["Trace-Id"] = incoming_trace_id

        incoming_user_id = LogContext.getcontext("user_id")
        if incoming_user_id:
            request.headers["User-Id"] = incoming_user_id
        request.headers["Span-Id"] = (
            LogContext.getcontext("span_id") or generate_trace_id()
        )
