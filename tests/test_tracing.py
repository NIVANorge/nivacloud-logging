import json
import re

import aiohttp
import pytest
import requests
from flask import Flask, jsonify

from nivacloud_logging.aiohttp_trace import create_trace_config
from nivacloud_logging.flask_trace import TracingMiddleware
from nivacloud_logging.log_utils import setup_logging, LogContext
from nivacloud_logging.requests_trace import TracingAdapter


def _create_tracing_requests_session():
    r = requests.Session()
    a = TracingAdapter()
    r.mount('http://', a)
    return r


def _is_trace_like(s):
    return re.match('[a-f0-9]+', s)


# Requests
def test_requests_generate_trace_id_if_missing():
    setup_logging()
    session = _create_tracing_requests_session()
    result = session.get('http://httpbin.org/headers')
    headers = result.json()['headers']

    assert 'Trace-Id' in headers
    assert _is_trace_like(headers.get('Trace-Id'))


def test_requests_trace_id_is_picked_up_from_context():
    setup_logging()
    session = _create_tracing_requests_session()
    with LogContext(trace_id='abc123'):
        result = session.get('http://httpbin.org/headers')
        headers = result.json()['headers']
        assert headers.get('Trace-Id') == 'abc123'


# Flask
def test_flask_trace_id_is_injected(capsys):
    app = Flask(__name__)
    app.wsgi_app = TracingMiddleware(app.wsgi_app)

    setup_logging()

    @app.route("/")
    def hello():
        return jsonify({"Trace-ID": LogContext.getcontext("trace_id")})

    client = app.test_client()
    r = client.get("/", headers={'Trace-ID': '123abc'}).json
    assert r.get('Trace-ID') == "123abc"

    (out, _) = capsys.readouterr()
    parsed_output = json.loads(out)
    assert parsed_output['trace_id'] == '123abc'


# aiohttp client
@pytest.mark.asyncio
async def test_aiohttp_generate_trace_id_if_missing():
    setup_logging()
    async with aiohttp.ClientSession(trace_configs=[create_trace_config()]) as session:
        async with session.get('http://httpbin.org/headers') as response:
            r = await response.json()
            assert _is_trace_like(r['headers'].get('Trace-Id'))


@pytest.mark.asyncio
async def test_aiohttp_trace_id_is_picked_up_from_context():
    setup_logging()
    async with aiohttp.ClientSession(trace_configs=[create_trace_config()]) as session, \
            LogContext(trace_id='abc123'), \
            session.get('http://httpbin.org/headers') as response:
        r = await response.json()
        assert r['headers'].get('Trace-Id') == 'abc123'
