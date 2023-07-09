"""
AD/Operations
Arek Gorzawski 2021, ESS
"""
from datetime import datetime, timedelta
import dateutil.parser

DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


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
    :param end_date: default is None, that translates into datetime.now()
    :return: two datetime objects for the start and the end date

    :raises ValueError if wrong type of objects provided
    """

    if start_date is None:
        raise ValueError("Cannot validate NONE start_date")

    if end_date is None:
        end_date = datetime.now()

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
    if isinstance(date, str):
        date = dateutil.parser.parse(date)
    elif not isinstance(date, datetime):
        raise ValueError(f"date string of wrong type {type(date)}")
    return date


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
    Formats the provided object or string (according to the input format) into the Archiver date format,
    in datetime().isoformat()+Z

    :param date_obj: date object (string or datetime)
    :param date_input_format: default "%Y-%m-%d %H:%M:%S"
    :return: ESS Archiver formatted date string
    """
    date_obj = getDateTimeObj(date_obj)
    return date_obj.isoformat() + "Z"
