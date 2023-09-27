"""
ESS 2021
Authors:
    A.Gorzawski <arek.gorzawski@ess.eu>
"""
import warnings
from datetime import datetime, timedelta
from abc import ABC
import epics
import math
import numpy as np
import pandas
from .archiver import Archiver


class WaveformCollector(ABC):
    """
    An abstract class for waveform collectors
    """

    def __init__(self, PV, roi_indexes: tuple = None, roi_use_on_final=True, callback=None, callback_delay_in_seconds=1, **kwargs):
        """
        Constructor for the abstract WaveformCollector class.

        :param PV: name of the PV (or PVs)
        :param roi_indexes: definition of the Region Of Interest, required a tuple of indexes like (1,10),
                                use .updateROI() if need to define the ROI in relative units.
        :param roi_use_on_final: default True, indicates the automatic recalculation of the the defined ROI
                                    after each acquisition.
        :param callback: call back function to be call on data update, structure: callback(PV=name,
                            dataframe=pandas.dataframe, lastCheck=lastupdatetime)
        :param callback_delay_in_seconds: delay between two callbacks
        """
        self._PV = PV
        self._roi_indexes = roi_indexes
        self._roi_use_on_final = roi_use_on_final
        if callback is None:
            warnings.warn("You have not defined the callback function! dev>null will be used.")
            callback = self._null_callback
        self._callback = callback
        self._callback_delay = timedelta(seconds=callback_delay_in_seconds)
        self._callback_last_call = datetime.now()
        self._dataframe = pandas.DataFrame(columns=["time", "secs", "secs_nanos", "val"])
        # TODO make conf with columns names across archiver and waveforms dataframes

    def getLastWaveform(self, timestamp=None, last=1) -> pandas.DataFrame:
        """
        Returns the last (n) waveforms from the collector's buffer.

        :param timestamp: default None, if given, all waveforms younger than given date. NOTE: not implemented yet!
        :param last: number of last waveforms to return
        :return:
        """
        if timestamp is None:
            toReturn = self._dataframe.tail(last)
            self._recalculate_ROI_value(toReturn)
            return toReturn
        else:
            # TODO use last available value as interpolation strategy
            raise NotImplementedError("Only last acquisition available for now, use: timestamp=None.")

    def getAllWaveforms(self) -> pandas.DataFrame:
        """
        :return: all buffered waveforms with additional column val_roi, that has an average value in the roi region
        """
        toReturn = self._dataframe.copy()  # TODO to be checked how it goes with the performance
        self._recalculate_ROI_value(toReturn)
        return toReturn

    def getROITrace(self) -> pandas.DataFrame:
        """
        :return: a simplified dataframe only with the time and average value in the roi region
        """
        return self.getAllWaveforms()[["time", "val_roi"]]

    def getColumns(self):
        """
        :return: column names that are available in the collector
        """
        return list(self._dataframe.columns)

    def getPV(self):
        return self._PV

    def updateROI(self, roi_indexes: tuple, sample_length=None):
        """
        Updates current settings for ROI
        :param roi_indexes: a tuple with start and end index, or relative timing if sample_length is defined,
        :param sample_length: default None, if not None the range of the roi can be provided in the absolute timing.
                              Should be added in the same unit as provided range.
                              Eg. roi_indexes in us (200, 300), sample_length=10
        :return: None
        """
        if not isinstance(roi_indexes, tuple) and len(roi_indexes) != 2:
            raise ValueError("Wrong ROI settings provided!")
        if sample_length is not None and sample_length > 0:
            self._roi_indexes = (int(roi_indexes[0] / sample_length), int(roi_indexes[1] / sample_length))
        else:
            self._roi_indexes = roi_indexes

    def getROI(self):
        """
        Returns the actual ROI indexes defined
        :return:
        """
        return self._roi_indexes

    def _recalculate_ROI_value(self, df):
        if self._dataframe.empty:
            return
        if self._roi_use_on_final and self._roi_indexes is not None and len(self._roi_indexes) == 2 and self._roi_indexes[0] < self._roi_indexes[1]:
            df["val_roi"] = df.apply(lambda row: np.mean(row["val"][self._roi_indexes[0] : self._roi_indexes[1]]), axis=1)
        else:
            df["val_roi"] = df.apply(lambda row: math.nan)

    def _null_callback(self, **kwargs):
        pass  # an empty callback


class CommonRealTimeWaveformCollector(WaveformCollector):
    """
    Class that provides an additional support for the rolling buffer.
    """

    def __init__(self, PV, data_buffer=3 * 60, **kwargs):
        """
        :param PV: PV to follow up
        :param data_buffer: length of the rolling buffer in seconds
        :param kwargs: any arguments that may be taken by an abstract WaveformCollector
        """
        super().__init__(PV, **kwargs)
        self._data_buffer = data_buffer

    def clearData(self):
        self._dataframe = self._dataframe[0:0]

    def _append(self, time, val, secs, secs_nanos):
        self._dataframe = pandas.concat(
            [self._dataframe, pandas.DataFrame([{"time": time, "val": val, "secs": secs, "secs_nanos": secs_nanos}])], ignore_index=True
        )

    def _update_buffer_and_call_callback(self, now):
        # drop older than collector's buffer
        oldest_to_keep = now - timedelta(seconds=self._data_buffer)
        self._dataframe.drop(self._dataframe[self._dataframe["time"] < oldest_to_keep].index, inplace=True)
        # check if call the external callback
        checkTime = datetime.now()
        if checkTime > self._callback_last_call + self._callback_delay:
            self._callback_last_call = checkTime
            self._callback(PV=self._PV, dataframe=self.getAllWaveforms(), lastCheck=checkTime)
        else:
            pass


class PVWaveformCollector(CommonRealTimeWaveformCollector):
    def __init__(self, PV: str, **kwargs):
        """
        Implementation of the WaveformCollector.

        Initialises PV waveform data collector. It uses PV from pyepics, use `connection_timeout` (default 3s)
        to adjust the waiting time

        :param PV: name of the pv
        :param callback: an external function to call
        :param callback_delay_in_seconds: a delay at which to call an external function, default 1s
        :param data_buffer: default 180s,
        """
        if not isinstance(PV, str):
            raise ValueError("Use one WaveformCollector per one PV")
        super().__init__(PV, **kwargs)
        self._epicsPV = epics.PV(
            self._PV,
            connection_timeout=kwargs.get("connection_timeout", 1),
            count=kwargs.get("count", None),
            auto_monitor=kwargs.get("auto_monitor", True),
        )
        self._epicsPV.add_callback(self._execute_callback)

    def _execute_callback(self, pvname=None, value=None, char_value=None, **kwargs):
        timestamp = datetime.fromtimestamp(kwargs["timestamp"])
        # append new
        self._append(timestamp, value, None, kwargs["timestamp"])
        self._update_buffer_and_call_callback(timestamp)


class ManyPVSWaveformCollector(CommonRealTimeWaveformCollector):
    def __init__(self, PVS: list, **kwargs):
        """
        Implementation of the WaveformCollector.

        Establish a monitor to provided PVs (representing a scalar PV).
        In the contained dataframe, one can see an array of the last value for each PV


        :param PVS: name of the pvs to be subscribed to
        :param callback: an external function to call
        :param callback_delay_in_seconds: a delay at which to call an external function, default 1s
        :param data_buffer: default 180s,
        """
        super().__init__(PV=list(PVS), **kwargs)
        self._roi_use_on_final = False
        timestamp = datetime.now()
        self._append(timestamp, [0 for pv in PVS], None, timestamp.timestamp())
        for PV in PVS:
            print("Registered '{}' for camonitoring".format(PV))
            epics.camonitor(PV, callback=self._execute_callback)

    def _execute_callback(self, pvname=None, value=None, char_value=None, **kwargs):
        if isinstance(value, list):
            warnings.warn("Subscribed PV {} is a waveform... skipping.".format(pvname))
            return None
        PVIndex = self._PV.index(pvname)
        timestamp = datetime.fromtimestamp(kwargs["timestamp"])
        try:
            newValueToBeSaved = [i for i in self._dataframe.iloc[[-1]]["val"].values[0]]  # TODO this one is fishy...
            newValueToBeSaved[PVIndex] = value
            self._append(timestamp, newValueToBeSaved, None, kwargs["timestamp"])
            self._update_buffer_and_call_callback(timestamp)
        except:
            pass


class ArchiverWaveformCollector(WaveformCollector):
    def __init__(self, PV, start_date, end_date=None, archiver_url=None, force_non_archived=False, max_number_of_hours_back=24, **kwargs):
        """
        Implementation of the WaveformCollector.

        Initialises an Archiver collector that connects to the service, extracts the data and listens to any new incoming (NOT YET IMPLEMENTED!)

        :param PV: name of the pv
        :param start_date: start date
        :param end_date: if None, it will used now()
        """
        if not isinstance(PV, str):
            raise ValueError("Use one WaveformCollector per one PV")
        super().__init__(PV, **kwargs)
        self._archiver = Archiver(archiver_url=archiver_url)
        self._dataframe = self._fetch_values(
            PV, start_date=start_date, end_date=end_date, force_non_archived=force_non_archived, max_number_of_hours_back=max_number_of_hours_back
        )

        # TODO initialize the auto refresh to call self._callback()

    def _fetch_values(self, PV, start_date, end_date=None, force_non_archived=False, max_number_of_hours_back=24):
        return self._archiver.getWaveform(
            PV, start_date=start_date, end_date=end_date, force_non_archived=force_non_archived, max_number_of_hours_back=max_number_of_hours_back
        )
