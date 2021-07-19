"""
ESS 2021
Authors:
    A.Gorzawski <arek.gorzawski@ess.eu>
    E.Laface    <emmanuele.laface@ess.eu>
"""
import warnings

from .timeutils import validateTimeStamps
from .codes import EpicsStatus, EpicsSeverity
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

    def getPVStatus(self, PV):
        raise NotImplementedError('Abstract implementation called, use concrete ones.')

    def getEmptyResult(self):
        raise NotImplementedError('Abstract implementation called, use concrete ones.')


class JsonEndPointArchiver(EndPoint):
    """
    JSON end point implementation for the ESS Archiver
    """

    def __init__(self, archiver_url=None):
        super().__init__(archiver_url)
        self.archiver_url_data = '{}:17668/retrieval/data/getData.json'.format(archiver_url)
        self.archiver_url_mgmt = '{}:17665/mgmt/bpl'.format(archiver_url)

    def getDataForPV(self, PV, start_date, end_date=None, entries_limit=None) -> pandas.DataFrame:
        start_date, end_date = validateTimeStamps(start_date, end_date)
        entries = self._countEntries(PV, start_date, end_date)
        if entries_limit is None:
            entries_limit = entries
        nth_url = '{}?pv=nth_{}({})&from={}&to={}'.format(self.archiver_url_data, int(entries // entries_limit),
                                                          PV,
                                                          start_date, end_date)
        json_data = requests.get(nth_url).json()[0]['data']
        dataset = pandas.read_json(json.dumps(json_data))
        if dataset.empty:
            # TODO consider retrieve iteratively to get the 'last' stored value
            #  and to produce the result DF with two lines (start and end time)
            warnings.warn('Empty dataset extracted for \'\''.format(PV))
            return dataset
        dataset['status_label'] = dataset.apply(lambda row: EpicsStatus(row['status']), axis=1)
        dataset['severity_label'] = dataset.apply(lambda row: EpicsSeverity(row['severity']), axis=1)
        dataset['secs_nanos'] = dataset['secs'] + dataset['nanos'] / 1e9
        dataset['time'] = pandas.to_datetime(dataset['secs_nanos'], unit='s')
        return dataset

    def _countEntries(self, PV, start_date, end_date) -> int:
        """
        Returns counted entries for the PV in a given time range

        :param PV:
        :param start_date:
        :param end_date:
        :return:
        """
        count_url = '{}?pv=count({})&from={}&to={}'.format(self.archiver_url_data, PV, start_date, end_date)
        json_data = requests.get(count_url).json()[0]['data']
        entries = 0
        for i in json_data:
            entries += i['val']
        return entries

    def getPVStatus(self, PV) -> dict:
        """
        :param PV:
        :return:
        """
        if isinstance(PV, str):
            PV = (PV,)
        url_to_check = '{}/getPVStatus?pv='.format(self.archiver_url_mgmt)
        for onePV in PV:
            url_to_check += onePV+","
        returnData = requests.get(url_to_check).json()
        return {returnDataItem['pvName']: returnDataItem for returnDataItem in returnData}

    def getEmptyResult(self):
        return pandas.DataFrame(columns=('time', 'val','status_label', 'severity_label', 'secs_nanos', 'secs',
                                         'nanos', 'status', 'severity'))