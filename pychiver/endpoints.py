"""
ESS 2021
Authors:
    A.Gorzawski <arek.gorzawski@ess.eu>
    E.Laface    <emmanuele.laface@ess.eu>
"""
import datetime
import warnings

from .timeutils import validateTimeStamps, validateTimeStampsReturnObjects, getDateTimeObj
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


def _fix(dataset: pandas.DataFrame, start_date, end_date) -> pandas.DataFrame:
    """
    Fixes the data set. by creating
    :param dataset:
    :param start_date:
    :param end_date:
    :return:
    """
    if len(dataset) < 2:
        from .calculations import LinearInterpolationStrategy
        warnings.warn('No value found in the the initial Time range, search extended to the earlier 24h.')
        new_times = [getDateTimeObj(start_date).timestamp(), getDateTimeObj(end_date).timestamp()]
        lis = LinearInterpolationStrategy(new_times)
        new_values = lis.getValues(dataset['secs'].values, dataset['val'].values)
        status = dataset['status'].values[-1]
        severity = dataset['severity'].values[-1]
        dataset.drop(dataset.index, inplace=True)
        for i in range(len(new_times)):
            dataset = dataset.append({'val': new_values[i],
                                            'secs': new_times[i],
                                            'status': status,
                                            'nanos': 0,
                                            'severity': severity}, ignore_index=True)

    dataset['status_label'] = dataset.apply(lambda row: EpicsStatus(row['status']), axis=1)
    dataset['severity_label'] = dataset.apply(lambda row: EpicsSeverity(row['severity']), axis=1)
    dataset['secs_nanos'] = dataset['secs'] + dataset['nanos'] / 1e9
    dataset['time'] = pandas.to_datetime(dataset['secs_nanos'], unit='s')
    return dataset


class JsonEndPointArchiver(EndPoint):
    """
    JSON end point implementation for the ESS Archiver
    """

    def __init__(self, archiver_url=None):
        super().__init__(archiver_url)
        self.archiver_url_data = '{}:17668/retrieval/data/getData.json'.format(archiver_url)
        self.archiver_url_mgmt = '{}:17665/mgmt/bpl'.format(archiver_url)

    def getDataForPV(self, PV, start_date, end_date=None, entries_limit=None,
                     max_number_of_hours_back=24) -> pandas.DataFrame:
        jsonReturn = self._getJSONRequest(PV, start_date, end_date=end_date, entries_limit=entries_limit,
                                          iteration=max_number_of_hours_back)
        # TODO think about putting the iterative search for an earlier value up to the Archiver class
        json_data = jsonReturn['data']
        dataset = pandas.read_json(json.dumps(json_data))
        if dataset.empty:
            warnings.warn('Empty dataset extracted for \'\''.format(PV))
            return dataset
        return _fix(dataset, start_date, end_date)

    def _getJSONRequest(self, PV, start_date, end_date=None, entries_limit=None,
                        entries_warning_limit=5000, iteration=24, verbose=False) -> dict:
        if verbose:
            print('No data found for \'{}\', trying earlier between: start:{} until {}'.format(PV, start_date, end_date))
        if iteration == 0:
            warnings.warn('No data found in the increased time window, returning empty result.')
            return {'data': []}
        start_date_str, end_date_str = validateTimeStamps(start_date, end_date)
        start_date, end_date = validateTimeStampsReturnObjects(start_date, end_date)
        entries = self._countEntries(PV, start_date_str, end_date_str)
        if entries_limit is None:
            entries_limit = entries
        if entries > entries_warning_limit:
            warnings.warn(
                'You are about to extract {} samples, this operation may take significant amount of time...'.format(
                    entries))
        nth_url = '{}?pv=nth_{}({})&from={}&to={}'.format(self.archiver_url_data, int(entries // entries_limit),
                                                          PV, start_date_str, end_date_str)

        toReturn = requests.get(nth_url).json()
        if len(toReturn[0].get('data', [])) == 0:
            return self._getJSONRequest(PV, start_date=start_date - datetime.timedelta(hours=1),
                                        end_date=start_date, entries_limit=entries_limit, iteration=iteration-1)
        return toReturn[0]

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
            url_to_check += onePV + ","
        returnData = requests.get(url_to_check).json()
        return {returnDataItem['pvName']: returnDataItem for returnDataItem in returnData}

    def getEmptyResult(self):
        return pandas.DataFrame(columns=('time', 'val', 'status_label', 'severity_label', 'secs_nanos', 'secs',
                                         'nanos', 'status', 'severity'))
