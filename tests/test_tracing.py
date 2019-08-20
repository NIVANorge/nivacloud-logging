import re

import requests

from nivacloud_logging.log_utils import setup_logging, LogContext
from nivacloud_logging.requests_trace import TracingAdapter


def _create_tracing_requests_session():
    r = requests.Session()
    a = TracingAdapter()
    r.mount('http://', a)
    return r


def _is_tracelike(s):
    return re.match('[a-f0-9]+', s)


def test_generate_trace_id_if_missing():
    setup_logging()
    session = _create_tracing_requests_session()
    result = session.get('http://httpbin.org/headers')
    headers = result.json()['headers']

    assert 'Trace-Id' in headers
    assert _is_tracelike(headers.get('Trace-Id'))


def test_trace_id_is_picked_up_from_context():
    setup_logging()
    session = _create_tracing_requests_session()
    with LogContext(trace_id='abc123'):
        result = session.get('http://httpbin.org/headers')
        headers = result.json()['headers']
        assert headers.get('Trace-Id') == 'abc123'
