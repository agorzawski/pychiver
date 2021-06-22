"""
AD/Operations
Arek Gorzawski 2021, ESS
"""
import datetime

VALID_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def validateTimeStamps(start_date, end_date=None) -> tuple:
    """
    Ensures that provided time stamps are of correct format.
    Accepted objects: string (with format ) or datetime object

    :param start_date:
    :param end_date: default is None, that translates into datetime.now()
    :return: two formatted strings for start and end date

    :raises ValueError if wrong type of objects provided
    """

    if start_date is None:
        raise ValueError('Cannot validate NONE start_date')

    if end_date is None:
        end_date = datetime.datetime.now()

    if not isinstance(start_date, datetime.datetime) and not isinstance(start_date, str):
        raise ValueError('Wrong start_date format (neither date time nor string)!')

    if not isinstance(end_date, datetime.datetime) and not isinstance(end_date, str):
        raise ValueError('Wrong end_date format (neither date time nor string)!')

    return getTimeStampFormatted(start_date), getTimeStampFormatted(end_date)


def getTimeStampFormatted(date_obj, date_input_format=VALID_DATE_FORMAT) -> str:
    """
    Formats the provided object or string (according to the input format) into the Archiver date format,
    in datetime().isoformat()+Z

    :param date_obj: date object (string or datetime)
    :param date_input_format: default "%Y-%m-%d %H:%M:%S"
    :return: ESS Archiver formatted date string
    """
    if isinstance(date_obj, datetime.datetime):
        pass
    else:
        date_obj = datetime.datetime.strptime(date_obj, date_input_format)
    return date_obj.isoformat() + "Z"
