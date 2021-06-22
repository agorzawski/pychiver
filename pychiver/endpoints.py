"""
ESS 2021
Authors:
    A.Gorzawski <arek.gorzawski@ess.eu>
    E.Laface    <emmanuele.laface@ess.eu>
"""

from .timeutils import validateTimeStamps
import pandas
import json
import requests


class EndPoint:
    """
    Abstract end point implementation for the Archiver
    """
    def __init__(self, archiver_url=None):
        self.archiver_url = archiver_url
        if self.archiver_url is None:
            raise ValueError('Cannot instantiate Archiver without a proper link to the service.')

    def getDataForPV(self, PV: str, start_date, end_date=None, entries_limit=None) -> pandas.DataFrame:
        raise NotImplementedError('Abstract implementation called, use concrete ones.')


class JsonEndPointArchiver(EndPoint):
    """
    JSON end point implementation for the ESS Archiver
    """
    def getDataForPV(self, PV, start_date, end_date=None, entries_limit=None) -> pandas.DataFrame:
        start_date, end_date = validateTimeStamps(start_date, end_date)
        entries = self._countEntries(PV, start_date, end_date)
        if entries_limit is None:
            entries_limit = entries
        nth_url = '{}?pv=nth_{}({})&from={}&to={}'.format(self.archiver_url, int(entries // entries_limit),
                                                          PV,
                                                          start_date, end_date)
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
