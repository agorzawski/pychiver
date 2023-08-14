"""
AD/Operations
Arek Gorzawski 2021, ESS
"""
from datetime import datetime, timedelta
import dateutil.parser
from dateutil import tz
from dateutil.tz import tzutc
import pytz
import warnings
from urllib.parse import quote

DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S.%f%z"


def getPeriods(date=datetime.now(), periods=1, period_length_in_hours=1) -> list:
    """
    Returns a list of tuples for start and end date of the defined period
    :param date: start date, default now.
    :param periods: number of defined periods, default 1
    :param period_length_in_hours: length of the
    :return:
    """
    periodsL = []
    now = date
    for one in range(0, periods):
        prev = now - timedelta(hours=period_length_in_hours)
        periodsL.append((prev, now))
        now = prev
    periodsL.reverse()
    return periodsL


def validateTimeStampsReturnObjects(start_date, end_date=None) -> tuple:
    """
    Ensures that provided time stamps are of correct format.
    Accepted objects: string (with format ) or datetime object

    :param start_date:
    :param end_date: default is None, that translates into datetime.utcnow()
    :return: two datetime objects for the start and the end date

    :raises ValueError if wrong type of objects provided
    """

    if start_date is None:
        raise ValueError("Cannot validate NONE start_date")

    if end_date is None:
        end_date = datetime.utcnow().replace(tzinfo=tz.UTC)

    if not isinstance(start_date, (datetime, str)):
        raise ValueError("Wrong start_date format (neither date time nor string)!")

    if not isinstance(end_date, (datetime, str)):
        raise ValueError("Wrong end_date format (neither date time nor string)!")

    return getDateTimeObj(start_date), getDateTimeObj(end_date)


def validateTimeStamps(start_date, end_date=None) -> tuple:
    """
    Ensures that provided time stamps are of correct format.
    Accepted objects: string (with format ) or datetime object

    :param start_date:
    :param end_date: default is None, that translates into datetime.now()
    :return: two formatted strings for the start and the end date

    :raises ValueError if wrong type of objects provided
    """
    s, e = validateTimeStampsReturnObjects(start_date, end_date)
    return _getTimeStampFormatted(s), _getTimeStampFormatted(e)


def getDateTimeObj(date) -> datetime:
    """
    Verify that a given string or datetime object is of the correct format. If not, then try to convert it while
    raising warnings, and if unsuccessful, raise ValueError. Otherwise return the well formatted datetime object.

    :param date: ISO-8601 compatible string (including UTC offset) -OR- datetime object with UTC dateutil timezone
    :return: datetime object in UTC (with dateutil, not pytz)
    :raises ValueError if input is incorrect or malformed.
    """
    if isinstance(date, str):
        date = dateutil.parser.parse(date)

    elif not isinstance(date, datetime):
        raise ValueError(f"date string of wrong type {type(date)}")

    # ISO-8601 compatible string or UTC aware datetime object received.
    if isinstance(date.tzinfo, dateutil.tz.tz.tzutc):
        return date

    # input is not great, not terrible. Convert to the better format.
    if date.tzinfo is None:
        warnings.warn("No time offset given. Assuming UTC.")
        return date.replace(tzinfo=tz.UTC)
    if isinstance(date.tzinfo, dateutil.tz.tz.tzoffset):
        # this is not necessarily bad. Future improvements should take note of offset given, and return data with the same offset, unless otherwise specified.
        warnings.warn("Non-UTC time offset given. Converting to UTC")
        return date.astimezone(tz.UTC)
    if isinstance(date.tzinfo, pytz.BaseTzInfo):
        # pytz is obsolete, and dateutil preferred.
        warnings.warn("pytz tzoffset received. Converting to dateutil tzinfo = tz.UTC")
        return date.astimezone(tzutc()).replace(tzinfo=tz.UTC)

    # No conversion attempts successful.
    raise ValueError(f"Unknown time offset: {type(date.tzinfo)}")


def getDateTimeString(date_obj: datetime, format=DEFAULT_DATE_FORMAT) -> str:
    """
    Converts datetime to string with given
    :param date_obj:
    :param format:
    :return: a string formated date
    """
    return datetime.strftime(date_obj, format)


def _getTimeStampFormatted(date_obj) -> str:
    """
    Formats the provided object or string (according to the input format) into URL-encoded string for the ESS archiver

    :param date_obj: date object (string or datetime)
    :param date_input_format: default "%Y-%m-%d %H:%M:%S"
    :return: ISO-8601 string formatted for passing as a GET request, compatible with ESS Archiver
    """
    date_obj = getDateTimeObj(date_obj)
    return quote(date_obj.isoformat())
