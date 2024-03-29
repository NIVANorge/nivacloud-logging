import json
import re

import aiohttp
import pytest
import requests
from flask import Flask, jsonify
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.testclient import TestClient

from nivacloud_logging.aiohttp_trace import create_client_trace_config
from nivacloud_logging.flask_trace import TracingMiddleware
from nivacloud_logging.log_utils import setup_logging, LogContext
from nivacloud_logging.requests_trace import TracingAdapter
from nivacloud_logging.starlette_trace import StarletteTracingMiddleware


def _create_tracing_requests_session():
    r = requests.Session()
    a = TracingAdapter()
    r.mount('http://', a)
    return r


def _is_trace_like(s):
    return re.match('[a-f0-9]+', s)


# Requests
def test_requests_generate_span_id_if_missing():
    setup_logging()
    session = _create_tracing_requests_session()
    result = session.get('http://httpbin.org/headers')
    headers = result.json()['headers']

    assert 'Span-Id' in headers
    assert _is_trace_like(headers.get('Span-Id'))


def test_requests_trace_id_is_picked_up_from_context():
    setup_logging()
    session = _create_tracing_requests_session()
    with LogContext(trace_id='abc123'):
        result = session.get('http://httpbin.org/headers')
        headers = result.json()['headers']
        assert headers.get('Trace-Id') == 'abc123'


def test_requests_trace_id_is_picked_up_from_context():
    setup_logging()
    session = _create_tracing_requests_session()
    with LogContext(user_id='10'):
        result = session.get('http://httpbin.org/headers')
        headers = result.json()['headers']
        assert headers.get('User-Id') == '10'


# Flask
def test_flask_trace_id_and_userid_is_injected(capsys):
    app = Flask(__name__)
    app.wsgi_app = TracingMiddleware(app.wsgi_app)

    setup_logging()

    @app.route("/")
    def hello():
        return jsonify({
            "Trace-Id": LogContext.getcontext("trace_id"),
            "User-Id": LogContext.getcontext("user_id"),
            "Span-Id": LogContext.getcontext("span_id"),
        })

    client = app.test_client()
    r = client.get("/", headers={'Trace-Id': '123abc', 'Span-Id': '456xyz', 'User-Id': '6'}).json
    assert r.get('Trace-Id') == "123abc"
    assert r.get('Span-Id') == '456xyz'
    assert r.get('User-Id') == '6'

    (out, _) = capsys.readouterr()
    parsed_output = json.loads(out)
    assert parsed_output['trace_id'] == '123abc'
    assert parsed_output['span_id'] == '456xyz'
    assert parsed_output['user_id'] == '6'

    # request with no trace/span/user headers set
    response2 = client.get("/").json
    assert response2["Trace-Id"] is not None
    assert response2["User-Id"] is None

    # check that a trace-id was generated and logged
    (out, _) = capsys.readouterr()
    parsed_output2 = json.loads(out)
    assert parsed_output2['trace_id'] == response2["Trace-Id"]


def test_starlette_trace_id_and_user_id_is_injected(capsys):
    app = Starlette(debug=True)
    app.add_middleware(StarletteTracingMiddleware)

    setup_logging()

    @app.route("/")
    async def hello(request):
        return JSONResponse({"Trace-Id": LogContext.getcontext("trace_id"), "User-Id": LogContext.getcontext("user_id")})

    client = TestClient(app)
    response = client.request(method="GET", url="/", headers={'Trace-Id': '123starlette', 'User-Id': '3'}).json()
    assert response["Trace-Id"] == "123starlette"
    assert response["User-Id"] == "3"

    (out, _) = capsys.readouterr()
    parsed_output = json.loads(out)
    assert parsed_output['trace_id'] == '123starlette'
    assert parsed_output['user_id'] == '3'

    # request with no trace/span/user headers set
    response2 = client.request(method="GET", url="/").json()
    assert response2["Trace-Id"] is not None
    assert response2["User-Id"] is None

    # check that a trace-id was generated and logged
    (out, _) = capsys.readouterr()
    parsed_output2 = json.loads(out)
    assert parsed_output2['trace_id'] == response2["Trace-Id"]


def test_starlette_span_id_is_picked_up_if_present(capsys):
    app = Starlette(debug=True)
    app.add_middleware(StarletteTracingMiddleware)

    setup_logging()

    @app.route("/")
    async def hello(request):
        return JSONResponse({"Span-Id": LogContext.getcontext("span_id")})

    client = TestClient(app)
    response = client.request(method="GET", url="/", headers={'Span-Id': 'starlettespanid'}).json()
    span_id = response["Span-Id"]
    assert span_id == "starlettespanid"

    (out, _) = capsys.readouterr()
    parsed_output = json.loads(out)
    assert parsed_output['span_id'] == "starlettespanid"


def test_starlette_span_id_is_generated_if_not_present(capsys):
    app = Starlette(debug=True)
    app.add_middleware(StarletteTracingMiddleware)

    setup_logging()

    @app.route("/")
    async def hello(request):
        return JSONResponse({"Span-Id": LogContext.getcontext("span_id")})

    client = TestClient(app)
    response = client.request(method="GET", url="/").json()
    span_id = response["Span-Id"]
    assert span_id is not None

    (out, _) = capsys.readouterr()
    parsed_output = json.loads(out)
    assert parsed_output['span_id'] == span_id


# aiohttp client
@pytest.mark.asyncio
async def test_aiohttp_generate_span_id_if_missing():
    setup_logging()
    async with aiohttp.ClientSession(trace_configs=[create_client_trace_config()]) as session:
        async with session.get('http://httpbin.org/headers') as response:
            r = await response.json()
            assert _is_trace_like(r['headers'].get('Span-Id'))


@pytest.mark.asyncio
async def test_aiohttp_trace_id_and_user_id_is_picked_up_from_context():
    setup_logging()
    async with aiohttp.ClientSession(trace_configs=[create_client_trace_config()]) as session, \
            LogContext(trace_id='abc123', user_id="5"), \
            session.get('http://httpbin.org/headers') as response:
        r = await response.json()
        assert r['headers'].get('Trace-Id') == 'abc123'
        assert r['headers'].get('User-Id') == '5'