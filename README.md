# Nivacloud-logging

A set of shared utils for setting up logging in a consistent way in
the [nivacloud](https://github.com/NIVANorge/nivacloud) ecosystem.

## Usage

Normally, you would just call `setup_logging()` and start logging and
set the `NIVACLOUD_PLAINTEXT_LOGS` if you want plaintext (human-readable)
logs instead of JSON. Default is JSON.

By default it will override all loggers to make sure that we get all the
logs through our handler. (So that everything is formatted as JSON and
ends up on stdout for Docker logs.) This feels slightly hacky, but I
think it's okay for our use-case. If you need to disable this, set
`NIVACLOUD_OVERRIDE_LOGGERS` to `0`.

```python
import logging
from nivacloud_logging.log_utils import setup_logging, LogContext, log_context

setup_logging()
logging.info("something happened")

with LogContext(my_id=123):
    logging.info("something happened with some context attached")
    
@log_context(something="foo")
def myfun(x):
    logging.info("I'm adding 1 to X and outputting 'something'!")
    return x + 1
```

### Runtime configuration

If you want to tweak the log level of a running service, you can 
send `SIGUSR1` to set `INFO` level debugging and `SIGUSR2` to set
`DEBUG` level debugging.

### With Gunicorn

To work with Gunicorn, you need to start `gunicorn` with the `--preload`
option so that `setup_logging` has a chance to run first. Also
`--access-logfile -` is needed for access logs.

### Running tests

```
$ python setup.py test
```

Or just run `pytest` if you have all packages installed.

#### Quirks

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
