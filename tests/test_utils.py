import unittest

from pychiver.timeutils import validateTimeStamps
import datetime

CORRECT_DATE = "2011-12-21 12:12:12"


class TestStartDateChecks(unittest.TestCase):

    def test_none_start_date(self):
        with self.assertRaises(ValueError):
            validateTimeStamps(start_date=None)

    def test_correct_date_time(self):
        validateTimeStamps(start_date=datetime.datetime.now())

    def test_correct_strng(self):
        validateTimeStamps(CORRECT_DATE)

    def test_not_valid_object(self):
        with self.assertRaises(ValueError):
            validateTimeStamps(66666)


class TestEndDateChecks(unittest.TestCase):

    def test_correct_string(self):
        validateTimeStamps(CORRECT_DATE, end_date=CORRECT_DATE)

    def test_correct_date_time(self):
        validateTimeStamps(start_date=datetime.datetime.now(), end_date=CORRECT_DATE)
