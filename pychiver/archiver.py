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

from .calculations import LinearInterpolationStrategy
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
                   time_base=None, strategy=LinearInterpolationStrategy, entries_limit=None):
        """
        Extracts PVs and aligns to the timestamps of the first PV in the list or separatly provided time base.


        :param PVS: list of PVS (string) to be extracted
        :param start_date:
        :param end_date:
        :param time_base: New time base to use, default None, then first PV timestamps' in the set is used
        :param strategy: Interpolation strategy to be used for the aligning, default LinearInterpolationStrategy
        :param entries_limit:
        :return: dict of DataFrames
        """
        raise NotImplementedError("Not implemented yet")
        # TODO finish first implementation for the interpolating with the provided time

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
        # TODO add simple PVInfo return
        raise NotImplementedError("Not implemented yet")
