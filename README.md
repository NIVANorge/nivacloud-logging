# Nivacloud-logging

A set of shared utilities for setting up logging and tracing in a
consistent way across [NIVA](https://www.niva.no/)'s Python-based
cloud services.

We're currently stuffing both regular application and system logs and
traces into [StackDriver](https://cloud.google.com/stackdriver/) in
Google Cloud, so this is for making (reasonably) sure that everything
logs in a JSON format that StackDriver understands.

## Usage

Normally, you would just call `setup_logging()` and start logging and
set the `NIVACLOUD_PLAINTEXT_LOGS` if you want plaintext (human-readable)
logs instead of JSON. Default is JSON.

If the `GIT_COMMIT_ID` environment variable is set, a `git_commit_id`
default context containing this will be added to all threads when
`setup_logging()` is executed.

By default it will override all loggers to make sure that we get all the
logs through our handler. (So that everything is formatted as JSON and
ends up on stdout for Docker logs.) This feels slightly hacky, but I
think it's okay for our use-case. If you need to disable this, set
`NIVACLOUD_OVERRIDE_LOGGERS` to `0`.

```python
import logging
from nivacloud_logging.log_utils import setup_logging, LogContext, log_context, log_exceptions

setup_logging()
logging.info("something happened")

with LogContext(my_id=123):
    logging.info("something happened with some context attached")

with LogContext(fjas="xyzzy"), log_exceptions():
    raise Exception("Log this exception, preserving context, then re-raise")

@log_context(something="foo")
def myfun(x):
    logging.info("I'm adding 1 to X and outputting 'something'!")
    return x + 1
```

### Runtime configuration

If you want to tweak the log level of a running service, you can
send `SIGUSR1` to set `INFO` level debugging and `SIGUSR2` to set
`DEBUG` level debugging.

### Running with Gunicorn

If you want access logs, pass `--access-logfile -` to Gunicorn. If
you want to override Gunicorn's log format before it starts
outputting logs, you can supply the `Logger` class from
`gunicorn_logger`, like this:

```
gunicorn --logger-class nivacloud_logging.gunicorn_logger.Logger
```

#### --preload

Don't use `--preload`, because we have a bunch of code like this:

```python
db = MyDb.connect()

@app.route("/")
def something():
    db.get("foo")
```

In cases like this, when you run Gunicorn with more than one worker
process, they may be sharing the file descriptors (sockets, in this
case) inherited from the parent process, and there will be no
synchronization between them, so in the worst case this may cause data
corruption. (It doesn't matter if the library used claims to be
thread-safe, because these are processes, not threads, so they don't
know about each other.)

### Tracing with Requests

In order to add `Span-Id`, `User-Id` and `Trace-Id` headers to outgoing requests,
there is an adapter that will pick up `trace_id`/`span_id` from the
*LogContext*, alternatively generating `Span-Id` if one doesn't exist.

```python
session = requests.Session()
session.mount('http://', TracingAdapter())
session.mount('https://', TracingAdapter())
r = session.get("https://httpbin.org/headers")
print(f"Span-Id is {r.json()['headers'].get('Span-Id')}")
```

### Tracing with aiohttp client

To add `Trace-Id` and `Span-Id` headers to outgoing requests, add a
`TraceConfig` to your session that adds trace IDs and span IDs to your
headers in the same way that the Requests tracing adapter does.

```python
from nivacloud_logging.aiohttp_trace import create_client_trace_config

async with aiohttp.ClientSession(trace_configs=[create_client_trace_config()]) as session, \
        LogContext(trace_id='abc123'), \
        session.get('https://httpbin.org/headers') as response:
    r = await response.json()
    print(f"Trace-ID is {r['headers'].get('Trace-Id')}")
```

### Tracing with Flask

To set `trace_id`, `user_id` and `span_id` in `LogContext` for incoming requests
based on the value of the `Trace-Id`, `User-Id` and `Span-Id` headers, use the
`TracingMiddleware` like so:

```python
app = Flask(__name__)
app.wsgi_app = TracingMiddleware(app.wsgi_app)
```

This will also generate log entries for each requests. (In addition to
access log entries. This should be improved at some point.)

### Tracing with Starlette

To get the same functionality as for Flask (see above), do this:

```python
app = Starlette()
app.add_middleware(StarletteTracingMiddleware)
```

## Running tests

```
$ python setup.py test
```

Or just run `pytest` if you have all packages installed.

### Quirks

With [pytest](https://docs.pytest.org/en/latest/) you would normally
use *caplog* to check log messages, but we're testing the logging
itself here, so it makes more sense to use *capsys* to read the
actual text output.

## Intended audience

This repository is primarily intended for internal use within
[Norwegian Institute for Water Research](https://www.niva.no/).

# Modules

## Structured logging

Applications that run in *nivacloud* run on Google Kubernetes
Engine. All logs from applications are aggregated via stdout to
[Stackdriver](https://cloud.google.com/stackdriver/) running in Google
Cloud.

When logs are aggregated from multiple sources via stdout, multi-line
logs end up as multiple log entries. One approach to this problem is to
log all log statements in json format. More details can be seen in the
[Google Cloud Structured Logging
documentation](https://cloud.google.com/logging/docs/structured-logging).

### StackdriverJsonFormatter

A opinionated log formatter which logs all log statements in a
structured JSON format, example:

```json
{
    "message": "something happened",
    "filename": "log_utils.py",
    "lineno": 52,
    "timestamp": "2019-03-22T09:26:21.084950",
    "severity": "INFO",
    "thread": 139978714621760,
    "pid": 4984,
    "my_id": 123
}
```
