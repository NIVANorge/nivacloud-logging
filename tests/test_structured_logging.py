import json
import logging

from nivacloud_logging.log_utils import setup_structured_logging


def test_should_log_jsons(capsys):
    setup_structured_logging()
    logging.info("something happened")

    (out, _) = capsys.readouterr()
    log_json = json.loads(out)

    assert log_json['message'] == 'something happened'
    assert log_json['filename'] == 'test_structured_logging.py'
    assert log_json['lineno'] is not None
    assert log_json["timestamp"] is not None
    assert log_json["severity"] == 'INFO'
    assert log_json["thread"] is not None
    assert log_json["pid"] is not None


def test_should_log_jsons_error(capsys):
    setup_structured_logging()
    logging.error("error error!")

    (out, _) = capsys.readouterr()
    log_json = json.loads(out)

    assert log_json["message"] == "error error!"
    assert log_json["filename"] == 'test_structured_logging.py'
    assert log_json["lineno"] is not None
    assert log_json["timestamp"] is not None
    assert log_json["severity"] == "ERROR"
    assert log_json["thread"] is not None
    assert log_json["pid"] is not None


def test_should_log_exceptions_as_json(capsys):
    setup_structured_logging()
    try:
        raise Exception("something horribly went wrong")
    except Exception:
        logging.exception("some error message")

    (out, _) = capsys.readouterr()
    log_json = json.loads(out)

    assert log_json["message"] == "some error message"
    assert "Traceback (most recent call last):" in log_json["exc_info"]
    assert "raise Exception(\"something horribly went wrong\")" in log_json["exc_info"]
    assert log_json["filename"] == 'test_structured_logging.py'
    assert log_json["lineno"] is not None
    assert log_json["timestamp"] is not None
    assert log_json["severity"] == "ERROR"
    assert log_json["thread"] is not None
    assert log_json["pid"] is not None


def test_should_not_log_below_log_level(capsys):
    setup_structured_logging(min_level=logging.WARNING)

    logging.info("this should not be logged")
    logging.warning("warning should be logged")

    (out, _) = capsys.readouterr()
    log_json = json.loads(out)

    assert log_json["message"] == "warning should be logged"
    assert log_json["filename"] == 'test_structured_logging.py'
    assert log_json["lineno"] is not None
    assert log_json["timestamp"] is not None
    assert log_json["severity"] == "WARNING"
    assert log_json["thread"] is not None
    assert log_json["pid"] is not None
