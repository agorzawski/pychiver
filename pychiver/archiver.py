"""
PyChiver -- A Python wrapping of ESS Archiver

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
        if isinstance(PV, tuple) or isinstance(PV, list):
            dataToReturn = {}
            for onePV in PV:
                if verbose:
                    print('Collecting data for', onePV)
                dataToReturn[onePV] = self.archiver.getDataForPV(onePV, start_date=start_date,
                                                                 end_date=end_date,
                                                                 entries_limit=entries_limit, )
            return dataToReturn
        else:
            return {PV: self.archiver.getDataForPV(PV, start_date=start_date, end_date=end_date,
                                                   entries_limit=entries_limit)}

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
        :param entries_limit: optional,
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
        df = self.get(PV, start_date, end_date=end_date, entries_limit=entries_limit, verbose=verbose)
        return calculateMovingAverage(df[PV], window=window,
                                      time_column=time_column, value_columns=value_columns,
                                      verbose=verbose)

    def getPulseData(self, cycle_id: int) -> pandas.DataFrame:
        """
        Returns data associated with the PulseId
        :param cycle_id:
        :return:
        """
        # TODO add when timing data in the archiver
        raise NotImplementedError("Not implemented yet")

    def check(self, PV: str):
        """
        Provides information on the requested PV(s)
        :param PV:
        :return: dict of PV to its data
        """
        return self.archiver.getPVStatus(PV)
