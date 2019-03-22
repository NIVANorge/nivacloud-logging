import logging
import unittest

from testfixtures import OutputCapture
import json

from nivacloud_logging.log_utils import setup_structured_logging


class StructuredLoggingTest(unittest.TestCase):

    def test_should_log_jsons(self):
        with OutputCapture() as log_capture:
            setup_structured_logging()
            logging.info("something happened")

            log_json = json.loads(log_capture.captured)
            self.assertEqual(log_json["message"], "something happened")
            self.assertEqual(log_json["filename"], 'test_structured_logging.py')
            self.assertIsNotNone(log_json["lineno"])
            self.assertIsNotNone(log_json["timestamp"])
            self.assertEqual(log_json["severity"], "INFO")
            self.assertIsNotNone(log_json["thread"])
            self.assertIsNotNone(log_json["pid"])

    def test_should_log_jsons_error(self):
        with OutputCapture() as l:
            setup_structured_logging()
            logging.error("error error!")

            log_json = json.loads(l.captured)
            self.assertEqual(log_json["message"], "error error!")
            self.assertEqual(log_json["filename"], 'test_structured_logging.py')
            self.assertIsNotNone(log_json["lineno"])
            self.assertIsNotNone(log_json["timestamp"])
            self.assertEqual(log_json["severity"], "ERROR")
            self.assertIsNotNone(log_json["thread"])
            self.assertIsNotNone(log_json["pid"])

    def test_should_log_exceptions_as_json(self):
        with OutputCapture() as log_capture:
            setup_structured_logging()
            try:
                raise Exception("something horribly went wrong")
            except Exception:
                logging.exception("some error message")

            log_json = json.loads(log_capture.captured)
            self.assertEqual(log_json["message"], "some error message")
            self.assertIn("Traceback (most recent call last):", log_json["exc_info"])
            self.assertIn("raise Exception(\"something horribly went wrong\")", log_json["exc_info"])
            self.assertEqual(log_json["filename"], 'test_structured_logging.py')
            self.assertIsNotNone(log_json["lineno"])
            self.assertIsNotNone(log_json["timestamp"])
            self.assertEqual(log_json["severity"], "ERROR")
            self.assertIsNotNone(log_json["thread"])
            self.assertIsNotNone(log_json["pid"])

    def test_should_not_log_below_log_level(self):
        with OutputCapture() as log_capture:
            setup_structured_logging(min_level=logging.WARNING)
            logging.info("this should not be logged")
            logging.warning("warning should be logged")

            log_json = json.loads(log_capture.captured)
            self.assertEqual(log_json["message"], "warning should be logged")
            self.assertEqual(log_json["filename"], 'test_structured_logging.py')
            self.assertIsNotNone(log_json["lineno"])
            self.assertIsNotNone(log_json["timestamp"])
            self.assertEqual(log_json["severity"], "WARNING")
            self.assertIsNotNone(log_json["thread"])
            self.assertIsNotNone(log_json["pid"])
