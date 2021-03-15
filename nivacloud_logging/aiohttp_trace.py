import aiohttp

from nivacloud_logging.log_utils import LogContext, generate_trace_id


def create_client_trace_config():
    """
    Returns a `TraceConfig` for aiohttp client sessions that appends Trace-Id and Span-Id.
    """

    async def on_request_start(session, trace_config_ctx, params):
        params.headers["Span-Id"] = (
            LogContext.getcontext("span_id") or generate_trace_id()
        )
        trace_id = LogContext.getcontext("trace_id")
        if trace_id:
            params.headers["Trace-Id"] = trace_id
        user_id = LogContext.getcontext("user_id")
        if user_id:
            params.headers["User-Id"] = user_id

    trace_config = aiohttp.TraceConfig()
    trace_config.on_request_start.append(on_request_start)
    return trace_config
