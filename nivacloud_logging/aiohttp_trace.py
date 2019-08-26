import aiohttp

from nivacloud_logging.log_utils import LogContext, generate_trace_id


def create_trace_config():
    """
    Returns a `TraceConfig` for aiohttp client sessions that appends a Trace-Id header based
    on either the `trace_id` log context or a newly generated trace ID.
    """

    async def on_request_start(session, trace_config_ctx, params):
        params.headers['Trace-Id'] = LogContext.getcontext("trace_id") or generate_trace_id()

    trace_config = aiohttp.TraceConfig()
    trace_config.on_request_start.append(on_request_start)
    return trace_config
