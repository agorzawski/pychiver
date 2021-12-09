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

import numpy

from .calculations import LinearInterpolationStrategy, alignDataFrames, calculateMovingAverage, findCloseTimestamps, \
    Edge
from .endpoints import JsonEndPointArchiver
from .domain import PVMetaInfo
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

    def get(self, PV, start_date, end_date=None, entries_limit=None, verbose=False, force_non_archived=False):
        """
        Returns the archiver data for one or many pvs within the given start_date and end_date.

        :param PV: one string or list of strings for PV to extract
        :param start_date:
        :param end_date: default None => now()
        :param entries_limit: default None, ie. all entries are extracted
        :param verbose: default False, if True the processing printout is provided
        :param force_non_archived: default False, when True, an attempt to extract archived data is made,
                may raise exception
        :return: dict of PV to a DataFrame
        """
        useSeparateLimits = False

        if isinstance(PV, (tuple, list)):
            if isinstance(entries_limit, tuple) and len(entries_limit) == len(PV):
                useSeparateLimits = True
            dataToReturn = {}
            for index, onePV in enumerate(PV):
                if verbose: print('Collecting data for', onePV)
                e_limit = entries_limit
                if useSeparateLimits:
                    e_limit = entries_limit[index]
                dataToReturn[onePV] = self._get(onePV, start_date=start_date, end_date=end_date,
                                                entries_limit=e_limit, verbose=verbose,
                                                force_non_archived=force_non_archived)[0]
            return dataToReturn
        else:
            if isinstance(entries_limit, tuple) and len(entries_limit) > 0:
                entries_limit = entries_limit[0]
            return {PV: self._get(PV, start_date=start_date, end_date=end_date,
                                  entries_limit=entries_limit, verbose=verbose,
                                  force_non_archived=force_non_archived)[0]}

    def getWaveform(self, onePV: str, start_date, end_date=None, verbose=False,
                    force_non_archived=False) -> pandas.DataFrame:
        """
        Returns an pandas DataFrame that contains a waveform

        :param onePV: PV to be extracted
        :param start_date:
        :param end_date: default None => now()
        :param verbose: default False, if True the processing printout is provided
        :param force_non_archived: default False, when True, an attempt to extract archived data is made anyway
        :return:
        """
        if not isinstance(onePV, str):
            raise ValueError('Only one waveform at the time! Too many or none PVs provided.')
        return self._get(onePV, start_date=start_date, end_date=end_date, verbose=verbose,
                         waveform_alert=False, force_non_archived=force_non_archived)[0]

    def getAligned(self, PVS: list, start_date, end_date=None,
                   time_base=None, strategy=LinearInterpolationStrategy,
                   entries_limit=None, time_column="secs_nanos", value_columns=("val",),
                   verbose=False,
                   force_non_archived=False) -> pandas.DataFrame:
        """
        Extracts PVs and aligns them to the timestamps of the first PV in the list or separately provided time base.
        Uses the provided InterpolationStrategy (default one LinearInterpolationStrategy)

        :param PVS: list of PVS (string) to be extracted
        :param start_date: start date,
        :param end_date: end date
        :param time_base: New time base to use, default None, then first PV timestamps' in the set is used.
                            If new provided, use epoch seconds.
        :param strategy: Interpolation strategy to be used for the aligning, default LinearInterpolationStrategy
        :param entries_limit: optional, default None, should be either a single None or a tuple of limits per requested PV
        :param time_column: optional, default 'time' column will be used
        :param value_columns: optional, default 'val' column will be used,
                     the alignment can be performed for many columns at the same time, provide a tuple.
        :param verbose: default False
        :param force_non_archived: default False, when True, an attempt to extract archived data is made anyway

        :return: a DataFrame with all PVS and their values
        """
        dict_of_dataframes = self.get(PVS, start_date, end_date=end_date,
                                      entries_limit=entries_limit, verbose=verbose,
                                      force_non_archived=force_non_archived)
        if not isinstance(dict_of_dataframes, dict):
            raise ValueError('Wrong data format provided. Dict of pandas.DataFrames expected, {} provided'. \
                             format(dict_of_dataframes.__class__))
        return alignDataFrames(dict_of_dataframes, time_base=time_base,
                               time_column=time_column, value_columns=value_columns,
                               InterpolationStrategyImpl=strategy, verbose=verbose)

    def getMovingAverage(self, PV, start_date, end_date=None, entries_limit=None, window=10,
                         time_column="secs_nanos", value_columns=("val",),
                         force_non_archived=False, verbose=False) -> pandas.DataFrame:
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
        :param force_non_archived:
        :param verbose:
        :return:
        """
        if isinstance(PV, list) or isinstance(PV, tuple) or isinstance(PV, dict):
            raise ValueError('Cannot handle more than one PV at the time. \
                                Use getAligned together with calculations.calculateMovingAverage')
        df, isWaveform = self._get(PV, start_date, end_date=end_date, entries_limit=entries_limit,
                                   force_non_archived=force_non_archived, verbose=verbose)
        if isWaveform:
            warnings.warn('Moving average over the waveform is not implemented! Returning simple DataForm')
            return df
        return calculateMovingAverage(df[PV], window=window,
                                      time_column=time_column, value_columns=value_columns,
                                      verbose=verbose)

    def compare(self, PVs: list, start_date, end_date=None,
                # index_of_reference_PV=0,
                compare_edge=Edge.FALLING,
                tolerance_in_seconds=0.1,
                force_non_archived=False,
                verbose=False) -> numpy.array:
        """
        Returns timestamps of the close occurrences of the RISING or FALLING for two

        :param PVs:
        :param start_date:
        :param end_date:
        :param compare_edge: compare the occurrences of the selected change
        :param tolerance_in_seconds: absolute (+/-) acceptable difference for simultaneous events
        :param force_non_archived:
        :param verbose:
        :return:
        """
        if len(PVs) != 2:
            raise ValueError('Only two signals expected for comparison!')

        # TODO see what to pass more, limits? etc..
        dfs = self.get(PVs, start_date=start_date, end_date=end_date, verbose=verbose,
                       force_non_archived=force_non_archived,)

        closeTimeStamps = findCloseTimestamps(dfs,
                                              tolerance_in_seconds=tolerance_in_seconds,
                                              edge_to_use=compare_edge,
                                              verbose=verbose)
        return closeTimeStamps

    def getPulseData(self, cycle_id: int) -> pandas.DataFrame:
        """
        Returns data associated with the PulseId
        :param cycle_id:
        :return:
        """
        # TODO add when timing data in the archiver
        # TODO waveforms should go as ArchiverCollectors
        raise NotImplementedError("Not implemented yet")

    def check(self, PV: str, type=PVMetaInfo.STATUS) -> dict:
        """
        Provides information on the requested PV(s)
        :param type: STATUS (default) returns info on PVs, INFO returns info on a given PVs
        :param PV: PVs to check status or info
        :return: dict of PV to its data
        """
        return self.archiver.getPVStatus(PV, type=type)

    def _get(self, onePV: str, start_date, end_date=None, entries_limit: int = None, verbose=False,
             waveform_alert=True, force_non_archived=False) \
            -> pandas.DataFrame:
        isWaveform = False
        status = self.check(onePV)
        df = self.archiver.getEmptyResult()
        if force_non_archived:
            warnings.warn('Skipping the check if {} is being archived in {}'.format(onePV, self.archiver_url))
        if 'Not' in status[onePV]['status'] and not force_non_archived:
            warnings.warn('Requested PV \'{}\' is NOT archived in {}, empty dataset will be returned.'
                          .format(onePV, self.archiver_url))
            pass
        else:
            df = self.archiver.getDataForPV(onePV, start_date=start_date, end_date=end_date,
                                            entries_limit=entries_limit,
                                            verbose=verbose)
        try:
            if len(df) > 0 and len(df['val'][0]):
                isWaveform = True
                if waveform_alert:
                    warnings.warn("The PV \'{}\' you have extracted is type of WAVEFORM with {} samples".
                                  format(onePV, len(df['val'][0])))
        except TypeError:
            pass  # This error is thrown on scalar types, due to len(df['val'])

        return df, isWaveform
