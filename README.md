# Nivacloud-logging

a set of shared utils for setting up logging in a consistent way in the nivacloud ecossytem

## Intended audience

This repository is primarily intended for internal use within Norwegian Institute for Water Research (https://www.niva.no/)


# modules

## structured logging

Applications that run in nivacloud run on Google Kubernetes Engine. All logs from applications are aggregated via stdout to [stackdriver](https://cloud.google.com/stackdriver/) running in google cloud.

When logs are aggregated from multiple sources via stdout, multi-line logs end up as muliple log entries. One approach to this problem is to log all log statements in json format. More details can be seen here https://cloud.google.com/logging/docs/structured-logging

### StackdriverJsonFormatter

A opinionated log formatter which logs all log statements in a structured json format, example:

```
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