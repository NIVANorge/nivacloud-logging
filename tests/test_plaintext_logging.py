import asyncio
import logging
import re
import sys
import threading
import time
from datetime import datetime

import pytest

from nivacloud_logging.log_utils import setup_logging, LogContext, auto_context


def _readout_log(capsys):
    (out, _) = capsys.readouterr()
    return out


def test_should_log_something(capsys):
    setup_logging(stream=sys.stdout, plaintext=True)
    logging.info("something happened")
    log = _readout_log(capsys)

    assert "--- Logging error ---" not in log
    assert "something happened" in log
    assert "INFO" in log
    assert "process=" in log
    assert "thread=" in log
    assert re.search(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}', log), "Missing or malformed timestamp"


def test_should_log_context(capsys):
    setup_logging(stream=sys.stdout, plaintext=True)
    with LogContext(trace_id=123):
        logging.info("something happened")
    log = _readout_log(capsys)

    assert "--- Logging error ---" not in log
    assert "something happened" in log
    assert "INFO" in log
    assert " [trace_id=123]" in log


def test_should_only_optionally_log_context(capsys):
    setup_logging(stream=sys.stdout, plaintext=True)
    logging.info("something happened")
    log = _readout_log(capsys)

    assert "--- Logging error ---" not in log
    assert "something happened" in log
    assert " [" not in log


def test_context_should_not_overwrite_existing_records(capsys):
    setup_logging(stream=sys.stdout, plaintext=True)
    with LogContext(created=123):
        logging.info("something happened")
    log = _readout_log(capsys)

    assert "--- Logging error ---" not in log
    assert "something happened" in log
    assert "created=123" not in log


def test_should_log_errors(capsys):
    setup_logging(stream=sys.stdout, plaintext=True)
    logging.error("error error!")
    log = _readout_log(capsys)

    assert "--- Logging error ---" not in log
    assert "error error!" in log
    assert "ERROR" in log


def test_should_log_exceptions(capsys):
    setup_logging(stream=sys.stdout, plaintext=True)

    # noinspection PyBroadException
    try:
        raise Exception("something horribly went wrong")
    except Exception:
        logging.exception("some error message")

    log = _readout_log(capsys)

    assert "--- Logging error ---" not in log
    assert "some error message" in log
    assert "Traceback (most recent call last):" in log
    assert 'raise Exception("something horribly went wrong")' in log
    assert "test_plaintext_logging.py" in log


def test_should_not_log_below_log_level(capsys):
    setup_logging(stream=sys.stdout, min_level=logging.WARNING, plaintext=True)

    logging.info("this should not be logged")
    logging.warning("warning should be logged")

    log = _readout_log(capsys)

    assert "--- Logging error ---" not in log

    assert "warning should be logged" in log
    assert "test_plaintext_logging.py" in log
    assert "WARNING" in log

    assert "INFO" not in log
    assert "this should not be logged" not in log


def test_should_handle_nested_context(capsys):
    setup_logging(stream=sys.stdout, plaintext=True)
    with LogContext(trace_id=123, foo="bar"):
        with LogContext(trace_id=42):
            logging.info("Something nested happened!")

    log = _readout_log(capsys)

    assert "--- Logging error ---" not in log
    assert "Something nested happened!" in log
    assert "trace_id=42" in log
    assert "foo='bar'" in log
    assert "INFO" in log


@pytest.mark.asyncio
async def test_should_handle_async_context(capsys):
    setup_logging(stream=sys.stdout, plaintext=True)

    async def busywork(n):
        await asyncio.sleep(0.01)
        return n + 1

    async with LogContext(trace_id=123):
        result = await busywork(0) + await busywork(121)
        async with LogContext(result=result):
            logging.info("Hei!")

    log = _readout_log(capsys)

    assert "--- Logging error ---" not in log
    assert "Hei!" in log
    assert "result=123" in log
    assert "INFO" in log


def test_should_handle_multiple_threads_with_contexts(capsys):
    # This test runs a child thread with a log context while
    # (hopefully, depending on timing)
    # a parent thread is also using a log context to make sure that
    # thread-local variables actually work the way I think.

    # Also note that for some reason that isn't entirely clear to
    # me, this test doesn't run with output to std.stderr. (It
    # probably works fine in non-testing situations!)
    setup_logging(stream=sys.stdout, plaintext=True)

    def worker():
        with LogContext(tid="child"):
            logging.info("Hi from child!")
            time.sleep(0.03)

    t = threading.Thread(target=worker)
    t.start()

    time.sleep(0.01)
    with LogContext(tid="parent"):
        logging.info("Hi from parent!")

    t.join()

    (log, _) = capsys.readouterr()
    [child, parent] = log.split('\n')[0:2]

    assert "tid='child'" in child
    assert "Hi from child!" in child
    assert "tid='parent'" in parent
    assert "Hi from parent!" in parent

    child_tid = re.search(r'thread=(\d+)', child).group(1)
    parent_tid = re.search(r'thread=(\d+)', parent).group(1)
    assert child_tid != parent_tid

    assert "INFO" in child
    assert "INFO" in parent

    assert "--- Logging error ---" not in child
    assert "--- Logging error ---" not in parent


def test_should_handle_extra_parameters(capsys):
    setup_logging(stream=sys.stdout, plaintext=True)

    logging.info("Something extra happened!", extra={'xyzzy': 'qwerty'})

    log = _readout_log(capsys)

    assert "--- Logging error ---" not in log
    assert 'Something extra happened!' in log
    assert "xyzzy='qwerty'" in log


def test_extra_parameters_should_override(capsys):
    setup_logging(stream=sys.stdout, plaintext=True)

    with LogContext(trace_id=123, foo='bar'):
        logging.info("Something extra happened!", extra={'foo': 'quux'})

    log = _readout_log(capsys)

    assert "--- Logging error ---" not in log
    assert 'Something extra happened!' in log
    assert 'trace_id=123' in log
    assert "foo='quux'" in log


def test_should_work_with_nonroot_logger(capsys):
    setup_logging(stream=sys.stdout, plaintext=True)

    logger = logging.getLogger("nonroot")
    with LogContext(trace_id=123):
        logger.info("I'm not the root logger.")

    log = _readout_log(capsys)

    assert "--- Logging error ---" not in log
    assert "I'm not the root logger." in log
    assert "[trace_id=123]" in log


def test_should_read_environment_config(capsys, monkeypatch):
    monkeypatch.setenv('NIVACLOUD_PLAINTEXT_LOGS', '1')
    setup_logging(stream=sys.stdout)

    with LogContext(plaintexty="yes"):
        logging.info("Environment blah blah.")

    log = _readout_log(capsys)

    assert "--- Logging error ---" not in log
    assert "Environment blah blah." in log
    assert "[plaintexty='yes']" in log


def test_should_override_propagation(capsys):
    logger = logging.getLogger('foo')
    logger.propagate = False
    setup_logging(override=True, plaintext=True, stream=sys.stdout)
    logger.info('Hei')

    log = _readout_log(capsys)

    assert "--- Logging error ---" not in log
    assert 'Hei' in log


def test_should_not_log_on_non_override(capsys):
    logger = logging.getLogger('foo')
    logger.propagate = False
    setup_logging(override=False, plaintext=True, stream=sys.stdout)
    logger.info('Hei')

    log = _readout_log(capsys)

    assert "--- Logging error ---" not in log
    assert 'Hei' not in log


def test_should_handle_multiple_setup_calls(capsys):
    setup_logging(plaintext=True, stream=sys.stdout)
    setup_logging(plaintext=True, stream=sys.stdout)

    logging.info('Once only!')

    log: str = _readout_log(capsys)

    assert "--- Logging error ---" not in log
    assert log.count('Once only!') == 1


def test_should_format_datetimes_properly(capsys):
    setup_logging(plaintext=True, stream=sys.stdout)

    with LogContext(from_time=datetime(2019, 12, 24, 12, 34, 56, 0)):
        logging.info("Something with a datetime")

    log = _readout_log(capsys)

    assert "--- Logging error ---" not in log
    assert 'from_time="2019-12-24T12:34:56"' in log


def test_auto_context_should_only_add_requested_context(capsys):
    # noinspection PyUnusedLocal
    @auto_context("host", "user")
    def login(host, user, password):
        logging.info("Logging in")

    setup_logging(plaintext=True, stream=sys.stdout)
    login("ftp.example.com", "jane", "supersekrit")

    log = _readout_log(capsys)

    assert "host='ftp.example.com'" in log
    assert "user='jane'" in log
    assert "supersekrit" not in log


def test_auto_context_should_log_all_parameters_by_default(capsys):
    # noinspection PyUnusedLocal
    @auto_context()
    def lookup(host, *servers):
        logging.info("Doing lookup...")

    setup_logging(plaintext=True, stream=sys.stdout)
    lookup("ftp.example.com", "1.1.1.1", "8.8.8.8")

    log = _readout_log(capsys)

    assert "host='ftp.example.com'" in log
    assert "servers=('1.1.1.1', '8.8.8.8')" in log


def test_auto_context_on_instance_methods(capsys):
    class MyClass:
        # noinspection PyUnusedLocal
        @auto_context()
        def my_method(self, a):
            logging.info("Hi!")

    setup_logging(plaintext=True, stream=sys.stdout)
    c = MyClass()
    c.my_method(42)

    log = _readout_log(capsys)

    assert "a=42" in log
