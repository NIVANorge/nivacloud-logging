import logging

from nivacloud_logging.log_utils import generate_trace_id, LogContext, log_exceptions
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


def log_request(request: Request):
    logging.info(
        f"{request.method} {request.url.path} ",
        extra={
            "query_params": request.url.query,
            "user_agent": request.headers.get("user-agent"),
        },
    )


class StarletteTracingMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        contextvars = {
            "trace_id": request.headers.get("trace-id") or generate_trace_id(),
            "user_id": request.headers.get("user-id"),
            "span_id": request.headers.get("span-id") or generate_trace_id(),
        }

        contextvars_with_values = {
            k: v for k, v in contextvars.items() if v is not None
        }

        with LogContext(**contextvars_with_values), log_exceptions():
            log_request(request)
            return await call_next(request)
