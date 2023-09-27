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
    B.Bolling   <benjamin.bolling@ess.eu>
"""

import os
import warnings
from typing import Tuple

import numpy
from pandas import DataFrame

from .calculations import LinearInterpolationStrategy, alignDataFrames, calculateMovingAverage, findCloseTimestamps, Edge, Calculation, CalculationMode
from .domain import PVMetaInfo
from .endpoints import JsonEndPointArchiver
from . import config
from .instances import DEFAULT_ARCHIVER, DEFAULT_MAX_EXTRACTION_SIZE
from .timeutils import getDateTimeObj
from .analysis import find_same


class Archiver:
    def __init__(self, archiver_url=DEFAULT_ARCHIVER, DefaultEndPoint=JsonEndPointArchiver):
        """
        Initializes the archiver with a provided url. If no url provided,
        a system environment EPICS_ARCHIVER_URL is asked if not set raises ValueError

        :param archiver_url: an address for the archiver service
        :param DefaultEndPoint: implementation of the endpoint
        """
        self.archiver_url = archiver_url
        if self.archiver_url is None:
            self.archiver_url = os.getenv("EPICS_ARCHIVER_URL", None)
            if self.archiver_url is None:
                warnings.warn(
                    "Archiver URL was not provided nor set in the env. \
                                Set EPICS_ARCHIVER_URL in your env."
                )

        self.archiver = DefaultEndPoint(archiver_url=archiver_url)

    def get(
        self,
        PV,
        start_date,
        end_date=None,
        entries_limit=None,
        force_non_archived=False,
        max_number_of_hours_back=24,
        data_extraction_limit=DEFAULT_MAX_EXTRACTION_SIZE,
        calc=Calculation.NTH,
        calc_mode=CalculationMode.TOTAL,
    ):
        """
        Returns the archiver data for one or many pvs within the given start_date and end_date.
        Can rise an ExpectedDataSizeExceedsLimitError if expected data extraction exceeds the limit.

        :param PV: one string or list of strings for PV to extract
        :param start_date:
        :param end_date: default None => now()
        :param entries_limit: default None, ie. all entries are extracted
        :param calc: default cluster-side calculation applied for the extracted data, default=NTH ->
         only decimation coming from the entries_limit
        :param calc_mode: default is calculation over all time span, other option is BINNED, together with
         entries_limit returns binned calculation
        :param max_number_of_hours_back: default 24, specifies for how many hours back archiver should be asked
                            if no data is found in between the start and end date
        :param force_non_archived: default False, when True, an attempt to extract archived data is made,
                may raise exception
        :param data_extraction_limit: maximum (in bytes) allowed chunk of data to extract, default 50Mb,
                    can be forced to skip by setting None
        :return: dict of PV to a DataFrame
        """
        useSeparateLimits = False

        if isinstance(PV, (tuple, list)):
            if isinstance(entries_limit, tuple) and len(entries_limit) == len(PV):
                useSeparateLimits = True
            dataToReturn = {}
            for index, onePV in enumerate(PV):
                config.printVerbose("Collecting data for", onePV)
                e_limit = entries_limit
                if useSeparateLimits:
                    e_limit = entries_limit[index]
                dataToReturn[onePV] = self._get(
                    onePV,
                    start_date=start_date,
                    end_date=end_date,
                    entries_limit=e_limit,
                    force_non_archived=force_non_archived,
                    max_number_of_hours_back=max_number_of_hours_back,
                    calc=calc,
                    calc_mode=calc_mode,
                    data_extraction_limit=data_extraction_limit,
                )[0]
            return dataToReturn
        else:
            if isinstance(entries_limit, tuple) and len(entries_limit) > 0:
                entries_limit = entries_limit[0]
            return {
                PV: self._get(
                    PV,
                    start_date=start_date,
                    end_date=end_date,
                    entries_limit=entries_limit,
                    force_non_archived=force_non_archived,
                    max_number_of_hours_back=max_number_of_hours_back,
                    data_extraction_limit=data_extraction_limit,
                    calc=calc,
                    calc_mode=calc_mode,
                )[0]
            }

    def getAtTime(self, PVs: list, time: None) -> DataFrame:
        # TODO support finding PVs at one time, returns simple data frame with
        #  PV as a key / time (requested) / time (closes to requested)/ value
        # TODO may need InterpolationStrategy in the parameter -> see getAligned with externally provided timebase
        # TODO see with compare()
        raise NotImplementedError("Not implemented yet")

    def getWaveform(
        self, onePV: str, start_date, end_date=None, force_non_archived=False, max_number_of_hours_back=24, data_extraction_limit=DEFAULT_MAX_EXTRACTION_SIZE
    ) -> DataFrame:
        """
        Returns a pandas DataFrame that contains a waveform. ExpectedDataSizeExceedsLimitError if expected data extraction exceeds the limit

        :param onePV: PV to be extracted
        :param start_date:
        :param end_date: default None => now()
        :param force_non_archived: default False, when True, an attempt to extract archived data is made anyway
        :param data_extraction_limit: maximum (in bytes) allowed chunk of data to extract, default 50Mb,
                    can be forced to skip by setting None
        :return:
        """
        if not isinstance(onePV, str):
            raise ValueError("Only one waveform at the time! Too many or none PVs provided.")
        return self._get(
            onePV,
            start_date=start_date,
            end_date=end_date,
            waveform_alert=False,
            force_non_archived=force_non_archived,
            max_number_of_hours_back=max_number_of_hours_back,
            data_extraction_limit=data_extraction_limit,
        )[0]

    def getAligned(
        self,
        PVS: list,
        start_date,
        end_date=None,
        time_base=None,
        strategy=LinearInterpolationStrategy,
        entries_limit=None,
        time_column="secs_nanos",
        value_columns=("val",),
        force_non_archived=False,
        data_extraction_limit=DEFAULT_MAX_EXTRACTION_SIZE,
    ) -> DataFrame:
        """
        Extracts PVs and aligns them to the timestamps of the first PV in the list or separately provided time base.
        Uses the provided InterpolationStrategy (default one LinearInterpolationStrategy).
        Can rise an ExpectedDataSizeExceedsLimitError if expected data extraction exceeds the limit.

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
        :param force_non_archived: default False, when True, an attempt to extract archived data is made anyway
        :param data_extraction_limit: maximum (in bytes) allowed chunk of data to extract, default 50Mb,
                    can be forced to skip by setting None
        :return: a DataFrame with all PVS and their values
        """
        dict_of_dataframes = self.get(
            PVS, start_date, end_date=end_date, entries_limit=entries_limit, force_non_archived=force_non_archived, data_extraction_limit=data_extraction_limit
        )
        if not isinstance(dict_of_dataframes, dict):
            raise ValueError("Wrong data format provided. Dict of pandas.DataFrames expected, {} provided".format(dict_of_dataframes.__class__))
        return alignDataFrames(
            dict_of_dataframes,
            time_base=time_base,
            time_column=time_column,
            value_columns=value_columns,
            InterpolationStrategyImpl=strategy,
        )

    def getMovingAverage(
        self,
        PV,
        start_date,
        end_date=None,
        entries_limit=None,
        window=10,
        time_column="secs_nanos",
        value_columns=("val",),
        force_non_archived=False,
        data_extraction_limit=DEFAULT_MAX_EXTRACTION_SIZE,
    ) -> DataFrame:
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
        :param data_extraction_limit: maximum (in bytes) allowed chunk of data to extract, default 50Mb,
            can be forced to skip by setting None
        :return:
        """
        if isinstance(PV, list) or isinstance(PV, tuple) or isinstance(PV, dict):
            raise ValueError(
                "Cannot handle more than one PV at the time. \
                                Use getAligned together with calculations.calculateMovingAverage"
            )
        df, isWaveform = self._get(
            PV, start_date, end_date=end_date, entries_limit=entries_limit, force_non_archived=force_non_archived, data_extraction_limit=data_extraction_limit
        )
        if isWaveform:
            warnings.warn("Moving average over the waveform is not implemented! Returning simple DataForm")
            return df
        return calculateMovingAverage(df, window=window, time_column=time_column, value_columns=value_columns)

    def compare(
        self,
        PVs: list,
        start_date,
        end_date=None,
        # index_of_reference_PV=0,
        compare_edge=Edge.FALLING,
        tolerance_in_seconds=0.1,
        force_non_archived=False,
    ) -> numpy.array:
        """
        Returns timestamps of the close occurrences of the RISING or FALLING for two

        :param PVs:
        :param start_date:
        :param end_date:
        :param compare_edge: compare the occurrences of the selected change
        :param tolerance_in_seconds: absolute (+/-) acceptable difference for simultaneous events
        :param force_non_archived:
        :return:
        """
        if len(PVs) != 2:
            raise ValueError("Only two signals expected for comparison!")

        # TODO see what to pass more, limits? etc..
        dfs = self.get(
            PVs,
            start_date=start_date,
            end_date=end_date,
            force_non_archived=force_non_archived,
        )

        closeTimeStamps = findCloseTimestamps(dfs, tolerance_in_seconds=tolerance_in_seconds, edge_to_use=compare_edge)
        return closeTimeStamps

    def compareSameOccurrences(
        self,
        basePV,
        PVsToCheck,
        start_date,
        end_date=None,
        margin_seconds=1,
        value_down=0,
        value_up=1,
        entries_limit=None,
        data_extraction_limit=DEFAULT_MAX_EXTRACTION_SIZE,
    ) -> DataFrame:
        """
        Returns a DataFrame, with the timestamps, correlation and the base PV being off (duration). The check is done
        the following: for every value == value_down of the base, the time series (withing the given times +/- margin) is checked,
        if there is a change ( from value_up=> value down) this occurrence is marked as common, and the time until
        the base recovers to value_up is counted as duration.

        This functionality can give unfiltered data with correlations of what brought what systems.

        :param basePV: a PV to look for the individual changes from value_up -> value_down,
        :param PVsToCheck: pvs to check if at the basePV timestamps, the same change (value_up->down) is happening withing the margin_seconds,
        :param margin_seconds: default 1s, margin to find 'same occurrence',
        :param value_up: value consider as 'normal', default 1,
        :param value_down: vale considered as 'down'/'off', default 0,
        :param start_date: start date of the time window,
        :param end_date: end date of the time window,
        :param entries_limit:
        :param data_extraction_limit:
        :return:
        """
        allPvs = [basePV]
        for onePV in PVsToCheck:
            allPvs.append(onePV)
        data = self.get(
            allPvs,
            start_date=start_date,
            end_date=end_date,
            entries_limit=entries_limit,
            max_number_of_hours_back=0,
            data_extraction_limit=data_extraction_limit,
        )
        result = {}
        for onePV in PVsToCheck:
            a = find_same(data, base=basePV, against=onePV, margin_seconds=margin_seconds, value_up=value_up, value_down=value_down)
            result[onePV] = a
        dataAll = {"input": [], "timestamp": [], "duration": []}
        for onePV in PVsToCheck:
            for one in result[onePV].values():
                if one["common"]:
                    dataAll["input"].append(onePV)
                    dataAll["timestamp"].append(one["start"])
                    dataAll["duration"].append(one["duration"])

        return DataFrame.from_dict(dataAll)

    def getPulseData(self, cycle_id: int) -> DataFrame:
        """
        Returns data associated with the PulseId
        :param cycle_id:
        :return:
        """
        # TODO add when timing data in the archiver
        # TODO waveforms should go as ArchiverCollectors
        raise NotImplementedError("Not implemented yet")

    def check(self, PV: str, info_type=PVMetaInfo.STATUS, git_config_id=None) -> dict:
        """
        Provides information on the requested PV(s)
        :param info_type: STATUS (default) returns info on PVs, INFO returns info on a given PVs
        :param git_config_id: DEFAULT_ARCHIVER_CONF (default) returns info on which Archiver Configuration
                           files a set of PVs are found within for different URLs and how many times
        :param PV: PVs to check status or info
        :return: dict of PV to its data
        """
        return self.archiver.getPVStatus(PV, info_type=info_type, git_config_id=git_config_id)

    def _get(
        self,
        onePV: str,
        start_date,
        end_date=None,
        entries_limit: int = None,
        waveform_alert=True,
        force_non_archived=False,
        max_number_of_hours_back=24,
        calc=Calculation.NTH,
        calc_mode=CalculationMode.TOTAL,
        data_extraction_limit=DEFAULT_MAX_EXTRACTION_SIZE,
    ) -> Tuple[DataFrame, bool]:
        start_date = getDateTimeObj(start_date)
        if end_date is not None:
            end_date = getDateTimeObj(end_date)
        isWaveform = False
        status = self.check(onePV)

        df = self.archiver.getEmptyResult()
        if force_non_archived:
            warnings.warn(f"Skipping the check if {onePV} is being archived in {self.archiver_url}")
        if "Not" in status[onePV]["status"] and not force_non_archived:
            warnings.warn(f"Requested PV '{onePV}' is NOT archived in {self.archiver_url}, empty dataset will be returned.")
            pass
        else:
            df = self.archiver.getDataForPV(
                onePV,
                start_date=start_date,
                end_date=end_date,
                entries_limit=entries_limit,
                max_number_of_hours_back=max_number_of_hours_back,
                data_extraction_limit=data_extraction_limit,
                calc=calc,
                calc_mode=calc_mode,
            )
        try:
            if len(df) > 0 and len(df["val"][0]):
                isWaveform = True
                if waveform_alert:
                    warnings.warn(f"The PV '{onePV}' you have extracted is type of WAVEFORM with {len(df['val'][0])} samples")
        except TypeError:
            pass  # This error is thrown on scalar types, due to len(df['val'])

        return df, isWaveform
