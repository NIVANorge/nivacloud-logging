import asyncio
import logging
import re
import sys
import threading
import time

import pytest

from nivacloud_logging.log_utils import setup_logging, LogContext


def _readout_log(capsys):
    (out, _) = capsys.readouterr()
    return out


def _has_asctime_timestamp(s):
    return re.search(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}', s)


def test_should_log_something(capsys):
    setup_logging(stream=sys.stdout, plaintext=True)
    logging.info("something happened")
    log = _readout_log(capsys)

    assert "--- Logging error ---" not in log
    assert "something happened" in log
    assert "INFO" in log
    assert "pid=" in log
    assert "thread=" in log
    assert _has_asctime_timestamp(log)


def test_should_log_context(capsys):
    setup_logging(stream=sys.stdout, plaintext=True)
    with LogContext(trace_id=123):
        logging.info("something happened")
    log = _readout_log(capsys)

    assert "--- Logging error ---" not in log
    assert "something happened" in log
    assert "INFO" in log
    assert " [context: trace_id=123]" in log
    assert _has_asctime_timestamp(log)


def test_should_only_optionally_log_context(capsys):
    setup_logging(stream=sys.stdout, plaintext=True)
    logging.info("something happened")
    log = _readout_log(capsys)

    assert "--- Logging error ---" not in log
    assert "something happened" in log
    assert " [context:" not in log
    assert _has_asctime_timestamp(log)


def test_context_should_not_overwrite_existing_records(capsys):
    setup_logging(stream=sys.stdout, plaintext=True)
    with LogContext(asctime=123):
        logging.info("something happened")
    log = _readout_log(capsys)

    assert "--- Logging error ---" not in log
    assert "something happened" in log
    assert "asctime=123" not in log
    assert _has_asctime_timestamp(log)


def test_should_log_errors(capsys):
    setup_logging(stream=sys.stdout, plaintext=True)
    logging.error("error error!")
    log = _readout_log(capsys)

    assert "--- Logging error ---" not in log
    assert "error error!" in log
    assert "ERROR" in log
    assert _has_asctime_timestamp(log)


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
    assert _has_asctime_timestamp(log)


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

    assert _has_asctime_timestamp(log)


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
    assert _has_asctime_timestamp(log)


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
    assert _has_asctime_timestamp(log)


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

    assert _has_asctime_timestamp(child)
    assert _has_asctime_timestamp(parent)


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
    assert "[context: trace_id=123]" in log
    assert _has_asctime_timestamp(log)


def test_should_read_environment_config(capsys, monkeypatch):
    monkeypatch.setenv('NIVACLOUD_PLAINTEXT_LOGS', '1')
    setup_logging(stream=sys.stdout)

    with LogContext(plaintexty="yes"):
        logging.info("Environment blah blah.")

    log = _readout_log(capsys)

    assert "Environment blah blah." in log
    assert "[context: plaintexty='yes']" in log
    assert _has_asctime_timestamp(log)


def test_should_override_propagation(capsys):
    logger = logging.getLogger('foo')
    logger.propagate = False
    setup_logging(override=True, plaintext=True, stream=sys.stdout)
    logger.info('Hei')

    log = _readout_log(capsys)
    assert 'Hei' in log
    assert _has_asctime_timestamp(log)


def test_should_not_log_on_non_override(capsys):
    logger = logging.getLogger('foo')
    logger.propagate = False
    setup_logging(override=False, plaintext=True, stream=sys.stdout)
    logger.info('Hei')

    log = _readout_log(capsys)
    assert 'Hei' not in log
