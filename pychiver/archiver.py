"""
PyChiver -- A Python wrapping of ESS Archiver and Save and Restore

Copyright (c) ESS 2021

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
of the Software, and to permit persons to whom the Software is furnished to do
so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

Authors:
    A.Gorzawski <arek.gorzawski@ess.eu>
    E.Laface    <emmanuele.laface@ess.eu>
"""

import os
import warnings

from .calculations import LinearInterpolationStrategy, alignDataFrames, calculateMovingAverage
from .endpoints import JsonEndPointArchiver
import pandas


class Archiver:

    def __init__(self, archiver_url=None, DefaultEndPoint=JsonEndPointArchiver):
        """
        Initializes the archiver with a provided url. If no url provided,
        a system environment EPICS_ARCHIVER_URL is asked, if not set raises ValueError

        :param archiver_url: an address for the archiver service
        :param DefaultEndPoint: implementation of the endpoint
        """
        self.archiver_url = archiver_url
        if self.archiver_url is None:
            self.archiver_url = os.getenv('EPICS_ARCHIVER_URL', None)
            if self.archiver_url is None:
                warnings.warn("Archiver URL was not provided nor set in the env. \
                                Set EPICS_ARCHIVER_URL in your env.")

        self.archiver = DefaultEndPoint(archiver_url=archiver_url)

    def get(self, PV, start_date, end_date=None, entries_limit=None, verbose=False):
        """
        Returns the archiver data for one or many pvs within the given start_date and end_date.

        :param PV: one string or list of strings for PV to extract
        :param start_date:
        :param end_date: default None => now()
        :param entries_limit: default None, ie. all entries are extracted
        :param verbose: default False, if True the processing printout is provided
        :return: dict of PV to a DataFrame
        """
        useSeparateLimits = False

        if isinstance(PV, tuple) or isinstance(PV, list):
            if isinstance(entries_limit, tuple) and len(entries_limit) == len(PV):
                useSeparateLimits = True
            dataToReturn = {}
            for index, onePV in enumerate(PV):
                if verbose: print('Collecting data for', onePV)
                e_limit = entries_limit
                if useSeparateLimits:
                    e_limit = entries_limit[index]
                dataToReturn[onePV] = self._get(onePV, start_date=start_date, end_date=end_date,
                                                entries_limit=e_limit, verbose=verbose)[0]
            return dataToReturn
        else:
            if isinstance(entries_limit, tuple) and len(entries_limit) > 0:
                entries_limit = entries_limit[0]
            return {PV: self._get(PV, start_date=start_date, end_date=end_date,
                                  entries_limit=entries_limit, verbose=verbose)[0]}

    def getWaveform(self, onePV: str, start_date, end_date=None, verbose=False) -> pandas.DataFrame:
        """
        Returns an pandas DataFrame that contains a waveform

        :param onePV: PV to be extracted
        :param start_date:
        :param end_date: default None => now()
        :param verbose: default False, if True the processing printout is provided
        :return:
        """
        if not isinstance(onePV, str):
            raise ValueError('Only one waveform at the time! Too many or none PVs provided.')
        return self._get(onePV, start_date=start_date, end_date=end_date, verbose=verbose, waveform_alert=False)[0]

    def getAligned(self, PVS: list, start_date, end_date=None,
                   time_base=None, strategy=LinearInterpolationStrategy,
                   entries_limit=None, time_column="secs_nanos", value_columns=("val",),
                   verbose=False) -> pandas.DataFrame:
        """
        Extracts PVs and aligns them to the timestamps of the first PV in the list or separately provided time base.
        Uses the provided InterpolationStrategy (default one LinearInterpolationStrategy)

        :param PVS: list of PVS (string) to be extracted
        :param start_date:
        :param end_date:
        :param time_base: New time base to use, default None, then first PV timestamps' in the set is used. If new provided, use epoch seconds.
        :param strategy: Interpolation strategy to be used for the aligning, default LinearInterpolationStrategy
        :param entries_limit: optional, default None, should be a tuple of limits per requested PV
        :param time_column: optional,
        :param value_columns: optional,
        :param verbose: default False
        :return: a DataFrame with all PVS and their values
        """
        dict_of_dataframes = self.get(PVS, start_date, end_date=end_date,
                                      entries_limit=entries_limit, verbose=verbose)
        if not isinstance(dict_of_dataframes, dict):
            raise ValueError('Wrong data format provided. Dict of pandas.DataFrames expected, {} provided'. \
                             format(dict_of_dataframes.__class__))
        return alignDataFrames(dict_of_dataframes, time_base=time_base,
                               time_column=time_column, value_columns=value_columns,
                               InterpolationStrategyImpl=strategy, verbose=verbose)

    def getMovingAverage(self, PV, start_date, end_date=None, entries_limit=None, window=10,
                         time_column="secs_nanos", value_columns=("val",), verbose=False) -> pandas.DataFrame:
        """
        Retrieves the data for a given PV and calculates the moving average for a selected window.
        The resulting dataframe is cleared from all NaN cases.

        :param PV:
        :param start_date:
        :param end_date:
        :param entries_limit:
        :param window:
        :param time_column:
        :param value_columns:
        :param verbose:
        :return:
        """
        if isinstance(PV, list) or isinstance(PV, tuple) or isinstance(PV, dict):
            raise ValueError('Cannot handle more than one PV at the time. \
                                Use getAligned together with calculations.calculateMovingAverage')
        df, isWaveform = self._get(PV, start_date, end_date=end_date, entries_limit=entries_limit, verbose=verbose)
        if isWaveform:
            warnings.warn('Moving average over the waveform is not implemented! Returning simple DataForm')
            return df
        return calculateMovingAverage(df[PV], window=window,
                                      time_column=time_column, value_columns=value_columns,
                                      verbose=verbose)

    def getBooleanSignalsCompared(self, PVs: list, start_date, end_date=None,
                                  index_of_reference_PV=0,
                                  compare_edge=0, # TODO create an enum RISING FALLING
                                  tolerance_in_seconds=1) -> pandas.DataFrame:
        if len(PVs) < 2:
            raise ValueError('At least two signals expected to compare to')
        # TODO implement the core: import archiver PVs, perform smart align (including the tolerance)
        #  resulting arrays compare bitwise
        print(self.archiver_url)
        raise NotImplementedError('Not implemented yet')

    def getPulseData(self, cycle_id: int) -> pandas.DataFrame:
        """
        Returns data associated with the PulseId
        :param cycle_id:
        :return:
        """
        # TODO add when timing data in the archiver
        # TODO waveforms should go as ArchiverCollectors
        raise NotImplementedError("Not implemented yet")

    def check(self, PV: str) -> dict:
        """
        Provides information on the requested PV(s)
        :param PV:
        :return: dict of PV to its data
        """
        return self.archiver.getPVStatus(PV)

    def _get(self, onePV: str, start_date, end_date=None, entries_limit: int = None, verbose=False, waveform_alert=True) \
            -> pandas.DataFrame:
        isWaveform = False
        status = self.check(onePV)
        df = self.archiver.getEmptyResult()
        if 'Not' in status[onePV]['status']:
            warnings.warn('Requested PV \'{}\' is NOT archived in {}, empty dataset will be returned.'
                          .format(onePV, self.archiver_url))
            pass
        else:
            df = self.archiver.getDataForPV(onePV, start_date=start_date, end_date=end_date, entries_limit=entries_limit)
        try:
            if len(df) > 0 and len(df['val'][0]):
                isWaveform = True
                if waveform_alert: warnings.warn("The PV \'{}\' you have extracted is type of WAVEFORM with {} samples".
                                                 format(onePV, len(df['val'][0])))
        except TypeError:
            pass  # This error is thrown on scalar types, due to len(df['val'])

        return df, isWaveform
