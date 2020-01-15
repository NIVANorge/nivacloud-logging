import logging

from nivacloud_logging.log_utils import generate_trace_id, LogContext
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


def log_request(request: Request):
    logging.info(f"{request.method} {request.url.path} ", extra={"query_params": request.url.query})


class StarletteTracingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        trace_id = request.headers.get('trace-id')
        span_id = request.headers.get('span-id') or generate_trace_id()
        user_id = request.headers.get('user-id')

        if trace_id:
            async with LogContext(trace_id=trace_id, user_id=user_id, span_id=span_id):
                log_request(request)
                return await call_next(request)
        else:
            async with LogContext(span_id=span_id):
                log_request(request)
                return await call_next(request)
