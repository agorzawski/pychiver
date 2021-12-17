"""
AD/Operations
Arek Gorzawski 2021, ESS
"""
import datetime
import dateutil.parser



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
        raise ValueError('Cannot validate NONE start_date')

    if end_date is None:
        end_date = datetime.datetime.now()

    if not isinstance(start_date, (datetime.datetime, str)):
        raise ValueError('Wrong start_date format (neither date time nor string)!')

    if not isinstance(end_date, (datetime.datetime, str)):
        raise ValueError('Wrong end_date format (neither date time nor string)!')

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


def getDateTimeObj(date_obj) -> datetime.datetime:
    if isinstance(date_obj, str):
        date_obj = dateutil.parser.parse(date_obj)
    elif not isinstance(date_obj, datetime.datetime):
        raise ValueError(f"date string of wrong type {type(date_obj)}")
    return date_obj


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
