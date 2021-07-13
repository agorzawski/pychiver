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

    def __init__(self, PV: str,
                 roi_indexes: tuple = None,
                 callback=None,
                 callback_delay_in_seconds=1):
        """
        :param PV: name of the PV
        :param roi_indexes: a tuple with start index and the end index of the ROI calculation,
        numpy mean function is called
        """
        if not isinstance(PV, str):
            raise ValueError('Use one PVWaveFormCollector per one PV')
        self._PV = PV
        self._roi_indexes = roi_indexes
        if callback is None:
            warnings.warn('You have not defined the callback function! dev>null will be used.')
            callback = self._null_callback
        self._callback = callback
        self._callback_delay = timedelta(seconds=callback_delay_in_seconds)
        self._callback_last_call = datetime.now()
        self._dataframe = pandas.DataFrame(columns={'time', 'secs', 'secs_nanos', 'val'})
        # TODO make conf with columns names across archiver and waveforms dataframes

    def getLastWaveform(self, timestamp=None, last=1) -> pandas.DataFrame:
        if timestamp is None:
            toReturn = self._dataframe.iloc[[-1]]
            self._get_ROI(toReturn)
            return toReturn
        else:
            # TODO use last available value as interpolation strategy
            raise NotImplementedError('Only last acquisition available for now, with timestamp=None.')

    def getAllWaveforms(self) -> pandas.DataFrame:
        toReturn = self._dataframe.copy()  # TODO to be checked how it goes with the performance
        self._get_ROI(toReturn)
        return toReturn

    def updateROI(self, roi_indexes: tuple):
        self._roi_indexes = roi_indexes

    def _get_ROI(self, df):
        if self._roi_indexes is not None and len(self._roi_indexes) == 2 and self._roi_indexes[0] < self._roi_indexes[1]:
            df['val_roi'] = df.apply(lambda row: np.mean(row['val'][self._roi_indexes[0]:self._roi_indexes[1]]), axis=1)
        else:
            df['val_roi'] = df.apply(lambda row: math.nan)

    def _null_callback(self, **kwargs):
        pass # an empty callback


class PVWaveformCollector(WaveformCollector):

    def __init__(self, PV: str, data_buffer=3*60, **kwargs):
        """
        Initialises PV waveform data collector. It uses camonitor from pyepics.

        :param PV: name of the pv
        :param callback: an external function to call
        :param callback_delay_in_seconds: a delay at which to call an external function, default 1s
        :param data_buffer: default 180s,
        """
        super().__init__(PV, **kwargs)
        self._data_buffer = data_buffer
        epics.camonitor(self._PV, callback=self._execute_callback)

    def _execute_callback(self, pvname=None, value=None, char_value=None, **kwargs):
        timestamp = datetime.fromtimestamp(kwargs["timestamp"])
        # append new
        self._dataframe = self._dataframe.append({'time': timestamp,
                                                  'val': value,
                                                  'secs': None,
                                                  'secs_nanos': kwargs["timestamp"]}, ignore_index=True)
        # drop older than collector's buffer
        oldest_to_keep = timestamp - timedelta(seconds=self._data_buffer)
        self._dataframe.drop(self._dataframe[self._dataframe['time'] < oldest_to_keep].index, inplace=True)
        # check if call the external callback
        checkTime = datetime.now()
        if checkTime > self._callback_last_call + self._callback_delay:
            self._callback_last_call = checkTime
            self._callback(PV=self._PV, dataframe=self.getAllWaveforms(), lastCheck=checkTime)
        else:
            pass


class ArchiverWaveformCollector(WaveformCollector):

    def __init__(self, PV, start_date, end_date=None, refresh_delay=1, archiver_url=None, **kwargs):
        """
        Initialises an Archiver collector that exposes utility methods for dealing with waveforms

        :param PV:
        :param start_date:
        :param end_date:
        :param refresh_delay:
        """

        super().__init__(PV, **kwargs)
        self._archiver = Archiver(archiver_url=archiver_url)
        self._dataframe = self._fetch_values(PV, start_date=start_date, end_date=end_date)

        # TODO initialize the auto refresh to call self._callback()

    def _fetch_values(self, PV, start_date, end_date=None):
        return self._archiver.getWaveform(PV, start_date=start_date, end_date=end_date)

