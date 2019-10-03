import asyncio
import json
import logging
import os
import signal
import threading
import time
from datetime import datetime
from uuid import UUID

import math
import pytest

from nivacloud_logging.log_utils import setup_logging, LogContext, auto_context


def _readout_json(capsys):
    (out, _) = capsys.readouterr()
    return json.loads(out)


def test_should_log_jsons(capsys):
    setup_logging()
    logging.info("something happened")

    log_json = _readout_json(capsys)

    assert log_json["message"] == "something happened"
    assert log_json["filename"] == "test_structured_logging.py"
    assert log_json["lineno"] is not None
    assert log_json["timestamp"] is not None
    assert log_json["severity"] == "INFO"


def test_should_log_jsons_error(capsys):
    setup_logging()
    logging.error("error error!")

    log_json = _readout_json(capsys)

    assert log_json["message"] == "error error!"
    assert log_json["filename"] == "test_structured_logging.py"
    assert log_json["lineno"] is not None
    assert log_json["timestamp"] is not None
    assert log_json["severity"] == "ERROR"


def test_should_log_exceptions_as_json(capsys):
    setup_logging()

    # noinspection PyBroadException
    try:
        raise Exception("something horribly went wrong")
    except Exception:
        logging.exception("some error message")

    log_json = _readout_json(capsys)

    assert log_json["message"] == "some error message"
    assert "Traceback (most recent call last):" in log_json["exc_info"]
    assert 'raise Exception("something horribly went wrong")' in log_json["exc_info"]
    assert log_json["filename"] == "test_structured_logging.py"
    assert log_json["lineno"] is not None
    assert log_json["timestamp"] is not None
    assert log_json["severity"] == "ERROR"


def test_should_not_log_below_log_level(capsys):
    setup_logging(min_level=logging.WARNING)

    logging.info("this should not be logged")
    logging.warning("warning should be logged")

    log_json = _readout_json(capsys)

    assert log_json["message"] == "warning should be logged"
    assert log_json["filename"] == "test_structured_logging.py"
    assert log_json["severity"] == "WARNING"
    assert log_json["lineno"] is not None
    assert log_json["timestamp"] is not None


def test_should_include_context(capsys):
    setup_logging()
    with LogContext(trace_id=123):
        logging.info("Something mysterious happened!")

    log_json = _readout_json(capsys)

    assert log_json["message"] == "Something mysterious happened!"
    assert log_json["trace_id"] == 123
    assert log_json["severity"] == "INFO"
    assert log_json["lineno"] is not None
    assert log_json["timestamp"] is not None


def test_should_handle_nested_context(capsys):
    setup_logging()
    with LogContext(trace_id=123, foo="bar"):
        with LogContext(trace_id=42):
            logging.info("Something nested happened!")

    log_json = _readout_json(capsys)

    assert log_json["message"] == "Something nested happened!"
    assert log_json["trace_id"] == 42
    assert log_json["foo"] == "bar"
    assert log_json["severity"] == "INFO"
    assert log_json["lineno"] is not None
    assert log_json["timestamp"] is not None


def test_should_handle_extra_parameters(capsys):
    setup_logging()

    logging.info("Something extra happened!", extra={'foo': 'bar'})

    log_json = _readout_json(capsys)

    assert log_json['message'] == 'Something extra happened!'
    assert log_json['foo'] == 'bar'


def test_extra_parameters_should_override(capsys):
    setup_logging()

    with LogContext(trace_id=123, foo='bar'):
        logging.info("Something extra happened!", extra={'foo': 'quux'})

    log_json = _readout_json(capsys)

    assert log_json['message'] == 'Something extra happened!'
    assert log_json['trace_id'] == 123
    assert log_json['foo'] == 'quux'


def test_context_should_not_overwrite_existing_records(capsys):
    setup_logging()
    with LogContext(timestamp=123):
        logging.info("something happened")
    log_json = _readout_json(capsys)

    assert log_json['message'] == 'something happened'
    assert log_json['timestamp'] != 123


@pytest.mark.asyncio
async def test_should_handle_async_context(capsys):
    setup_logging()

    async def busywork(n):
        await asyncio.sleep(0.01)
        return n + 1

    async with LogContext(trace_id=123):
        result = await busywork(0) + await busywork(121)
        async with LogContext(result=result):
            logging.info("Hei!")

    log_json = _readout_json(capsys)

    assert log_json["message"] == "Hei!"
    assert log_json["result"] == 123
    assert log_json["severity"] == "INFO"
    assert log_json["lineno"] is not None
    assert log_json["timestamp"] is not None


def test_should_handle_multiple_threads_with_contexts(capsys):
    # This test runs a child thread with a log context while
    # (hopefully, depending on timing)
    # a parent thread is also using a log context to make sure that
    # thread-local variables actually work the way I think.
    setup_logging()

    def worker():
        with LogContext(tid="child"):
            logging.info("Hi from child!")
            time.sleep(0.02)

    t = threading.Thread(target=worker)
    t.start()

    time.sleep(0.01)
    with LogContext(tid="parent"):
        logging.info("Hi from parent!")

    t.join()

    (out, _) = capsys.readouterr()
    [child, parent] = [json.loads(s) for s in out.split("\n") if s]

    assert child["tid"] == "child"
    assert child["message"] == "Hi from child!"
    assert parent["tid"] == "parent"
    assert parent["message"] == "Hi from parent!"
    assert child["thread"] != parent["thread"]
    assert child["thread"] is not None
    assert child["process"] == parent["process"]
    assert child['process'] is not None
    assert child["severity"] == "INFO"
    assert parent["severity"] == "INFO"
    assert child['timestamp'] is not None
    assert parent['timestamp'] is not None


def test_should_work_with_nonroot_logger(capsys):
    setup_logging()
    logger = logging.getLogger("nonroot")
    with LogContext(trace_id=123):
        logger.info("I'm not the root logger.")

    log_json = _readout_json(capsys)

    assert log_json['message'] == "I'm not the root logger."
    assert log_json['trace_id'] == 123
    assert log_json['timestamp'] is not None


def test_should_read_environment_config(capsys, monkeypatch):
    monkeypatch.setenv('NIVACLOUD_PLAINTEXT_LOGS', '0')
    setup_logging()

    logging.info("Environment blah blah.")

    log_json = _readout_json(capsys)

    assert log_json['message'] == "Environment blah blah."
    assert log_json['timestamp'] is not None


def test_should_override_propagation(capsys):
    logger = logging.getLogger('foo')
    logger.propagate = False
    setup_logging(override=True)
    logger.info('Hei')

    log_json = _readout_json(capsys)
    assert log_json['message'] == 'Hei'


def test_should_not_log_on_non_override(capsys):
    logger = logging.getLogger('foo')
    logger.propagate = False
    setup_logging(override=False)
    logger.info('Hei')

    with pytest.raises(json.JSONDecodeError):
        _readout_json(capsys)


def test_should_handle_multiple_setup_calls(capsys):
    setup_logging()
    setup_logging()

    logging.info('Hei')

    # (Would throw exception if output was doubled.)
    log_json = _readout_json(capsys)

    assert log_json['message'] == 'Hei'


def test_auto_context_should_only_add_requested_context(capsys):
    # noinspection PyUnusedLocal
    @auto_context("host", "user")
    def login(host, user, password):
        logging.info("Logging in")

    setup_logging()
    login("ftp.example.com", "jane", "supersekrit")

    log_json = _readout_json(capsys)

    assert log_json["host"] == "ftp.example.com"
    assert log_json["user"] == "jane"
    assert "password" not in log_json


def test_auto_context_should_log_all_parameters_by_default(capsys):
    # noinspection PyUnusedLocal
    @auto_context()
    def lookup(host, *servers):
        logging.info("Doing lookup...")

    setup_logging()
    lookup("ftp.example.com", "1.1.1.1", "8.8.8.8")

    log_json = _readout_json(capsys)

    assert log_json["host"] == "ftp.example.com"
    assert log_json["servers"] == ["1.1.1.1", "8.8.8.8"]


def test_auto_context_on_instance_methods(capsys):
    class MyClass:
        # noinspection PyUnusedLocal
        @auto_context()
        def my_method(self, a):
            logging.info("Hi!")

    setup_logging()
    c = MyClass()
    c.my_method(42)

    log_json = _readout_json(capsys)

    assert log_json['a'] == 42


def test_should_handle_complex_context_data(capsys):
    setup_logging()

    class Sample:
        pass

    thing = {
        'my_id': UUID('7118ad7e-6e26-483a-a120-7ec176331354'),
        'time': datetime(2019, 12, 24, 12, 34, 56, 0),
        'tupled': ("foo", {'complex': complex(12, 45)}, 1, 1.2, -4, 1.4e-10),
        'class': Sample,
        'instance': Sample(),
        'nan': math.nan,
    }

    with LogContext(thing=thing):
        logging.info("Hi, I have bunch of stuff.")

    log_json = _readout_json(capsys)
    thing = log_json['thing']

    assert thing['my_id'] == '7118ad7e-6e26-483a-a120-7ec176331354'
    assert thing['time'] == '2019-12-24T12:34:56'
    assert ["foo", {"complex": {"real": 12.0, "imag": 45.0}}, 1, 1.2, -4, 1.4e-10] == thing["tupled"]
    assert math.isnan(thing['nan'])


def test_sigusr1_should_set_info_logging(capsys):
    setup_logging(min_level=logging.ERROR)
    logging.info("Not logged")
    os.kill(os.getpid(), signal.SIGUSR1)
    logging.info("This is logged")

    (out, _) = capsys.readouterr()
    outputs = [json.loads(s) for s in out.split("\n") if s]
    assert len(outputs) == 1, "Expecting single line of logging output"
    assert outputs[0]['message'] == 'This is logged'


def test_sigusr2_should_set_debug_logging(capsys):
    setup_logging(min_level=logging.INFO)
    logging.debug("Not logged")
    os.kill(os.getpid(), signal.SIGUSR2)
    logging.debug("THIS is logged")

    (out, _) = capsys.readouterr()
    outputs = [json.loads(s) for s in out.split("\n") if s]
    assert len(outputs) == 1, "Expecting single line of logging output"
    assert outputs[0]['message'] == 'THIS is logged'


def test_signal_handler_override_should_call_previous_handlers(capsys):
    myhandler_run_count = 0

    def myhandler(_s, _f):
        nonlocal myhandler_run_count
        myhandler_run_count += 1

    signal.signal(signal.SIGUSR2, myhandler)
    os.kill(os.getpid(), signal.SIGUSR2)

    setup_logging(min_level=logging.INFO)
    os.kill(os.getpid(), signal.SIGUSR2)
    logging.debug("Debugged!")

    log_json = _readout_json(capsys)
    assert log_json['message'] == 'Debugged!'
    assert myhandler_run_count == 2


def test_should_add_commit_it_from_environment(capsys, monkeypatch):
    monkeypatch.setenv('GIT_COMMIT_ID', 'd22b929')
    setup_logging()
    logging.info('Something committed')

    log_json = _readout_json(capsys)
    assert log_json['message'] == 'Something committed'
    assert log_json['git_commit_id'] == 'd22b929'


def test_should_not_add_commit_id_context_on_missing_env(capsys, monkeypatch):
    monkeypatch.setenv('GIT_COMMIT_ID', '')
    setup_logging()
    logging.info('Something committed')

    log_json = _readout_json(capsys)
    assert log_json['message'] == 'Something committed'
    assert 'git_commit_id' not in log_json
