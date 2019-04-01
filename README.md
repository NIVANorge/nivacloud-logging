# Nivacloud-logging

A set of shared utils for setting up logging in a consistent way in
the *nivacloud* ecosystem.

## Usage

```python
import logging
from nivacloud_logging.log_utils import setup_structured_logging

setup_structured_logging()
logging.info("something happened")
```

### Running tests

```
$ python setup.py test
```

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
    "pid": 4984
}
```
