"""
AD/Operations
Arek Gorzawski 2020, ESS
"""

import pandas
import json
import requests
import os
import datetime


class Archiver:
    """
    A class that provides the link to the ARCHIVER instance and exposes some convenience methods to access the stored data
    """

    def __init__(self, archiver_url=None):
        """
        Initializes the archiver with a provided url. If no url provided,
        a system environment EPICS_ARCHIVER_URL is asked, if not set raises ValueError

        :param archiver_url:
        """
        self.archiver_url = archiver_url
        if self.archiver_url is None:
            self.archiver_url = os.getenv('EPICS_ARCHIVER_URL', None)
        if self.archiver_url is None:
            raise ValueError('Cannot instantiate Archiver without a proper link to the service.\
                                Please set EPICS_ARCHIVER_URL in your env')

    def get(self, PV, start_date, end_date=None, decimate=1000, verbose=False) -> pandas.DataFrame:
        """
        Returns the archiver data for one or many pvs withing the given start_date and end_date.
        :param PV:
        :param start_date:
        :param end_date: default None => now()
        :param decimate: default 1000
        :return:
        """
        if isinstance(PV, tuple) or isinstance(PV, list):
            dataToReturn = {}
            for onePV in PV:
                if verbose:
                    print('Collecting ', onePV)
                dataToReturn[onePV] = self._getDataForPV(onePV, start_date=start_date,
                                                         end_date=end_date, decimate=decimate,)
            return dataToReturn
        else:
            return self._getDataForPV(PV, start_date=start_date, end_date=end_date, decimate=decimate)

    def _getDataForPV(self, PV, start_date, end_date=None, decimate=1000) -> pandas.DataFrame:
        start_date, end_date = validateTimeStamps(start_date, end_date)
        entries = self._countEntries(PV, start_date, end_date)
        nth_url = '{}?pv=nth_{}({})&from={}&to={}'.format(self.archiver_url, int(entries // decimate), PV, start_date,
                                                          end_date)
        json_data = requests.get(nth_url).json()[0]['data']
        dataset = pandas.read_json(json.dumps(json_data))
        dataset['time'] = pandas.to_datetime(dataset['secs'] + dataset['nanos'] / 1e9, unit='s')
        return dataset

    def _countEntries(self, PV, start_date, end_date) -> int:
        """
        Returns counted entries for the PV in a given time range

        :param PV:
        :param start_date:
        :param end_date:
        :return:
        """
        count_url = '{}?pv=count({})&from={}&to={}'.format(self.archiver_url, PV, start_date, end_date)
        json_data = requests.get(count_url).json()[0]['data']
        entries = 0
        for i in json_data:
            entries += i['val']
        return entries


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


def getTimeStampFormatted(date_obj, date_input_format="%Y-%m-%d %H:%M:%S") -> str:
    """
    Formats the provided object or string (according to the input format) into the Archiver date format,
    in datetime().isoformat()+Z
    :param date_obj:
    :param date_input_format:
    :return:
    """
    if isinstance(date_obj, datetime.datetime):
        pass
    else:
        date_obj = datetime.datetime.strptime(date_obj, date_input_format)
    return date_obj.isoformat() + "Z"
