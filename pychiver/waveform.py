"""
ESS 2021
Authors:
    A.Gorzawski <arek.gorzawski@ess.eu>
"""
import warnings
from datetime import datetime, timedelta
from abc import ABC
import epics
import pandas
from .archiver import Archiver


class WaveformCollector(ABC):
    """
    An abstract class for waveform collectors
    """

    def __init__(self, PV):
        if not isinstance(PV, str):
            raise ValueError('Use one PVWaveFormCollector per one PV')
        self._PV = PV
        self._dataframe = pandas.DataFrame(columns={'time', 'secs', 'secs_nanos', 'val'})
        # TODO make conf with columns names across archiver and waveforms dataframes

    def getLastWaveform(self, timestamp=None, last=1) -> pandas.DataFrame:
        if timestamp is None:
            return self._dataframe.iloc[[-1]]
        else:
            # TODO use last available value as interpolation strategy
            raise NotImplementedError('Only last acquisition available for now, with timestamp=None.')

    def getMeanInROI(self, timestamp=None, roi_start=0, roi_end=-1):
        # TODO get array of means for each waveforms
        pass

    def getAllWaveforms(self) -> pandas.DataFrame:
        return self._dataframe  # TODO consider deep copy


class PVWaveformCollector(WaveformCollector):

    def __init__(self, PV:str, callback=None, callback_delay_in_seconds=1, data_buffer=3*60):
        """
        Initialises PV waveform data collector. It uses camonitor from pyepics.

        :param PV: name of the pv
        :param callback: an external function to call
        :param callback_delay_in_seconds: a delay at which to call an external function, default 1s
        :param data_buffer: default 180s,
        """
        super().__init__(PV)
        if callback is None:
            warnings.warn('You have not defined the callback function! dev>null will be used.')
            callback = self._null_callback
        self._callback = callback
        self._callback_delay = timedelta(seconds=callback_delay_in_seconds)
        self._callback_last_call = datetime.now()
        self._data_buffer = data_buffer
        epics.camonitor(self._PV, callback=self._execute_callback, connection_timeout=1)

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
        checkTime = datetime.now()
        if checkTime > self._callback_last_call + self._callback_delay:
            self._callback_last_call = checkTime
            self._callback(PV=self._PV, dataframe=self.getAllWaveforms(), lastCheck=checkTime)
        else:
            pass

    def _null_callback(self, **kwargs):
        pass # an empty callback


class ArchiverWaveformCollector(WaveformCollector):

    def __init__(self, PV, start_date, end_date=None, refresh_delay=1):
        """
        Initialises an Archiver collector that exposes utility methods for dealing with waveforms

        :param PV:
        :param start_date:
        :param end_date:
        :param refresh_delay:
        """

        super().__init__(PV,)
        self._archiver = Archiver(archiver_url='http://archiver-01.tn.esss.lu.se')
        self._dataframe = self._fetch_values(PV, start_date=start_date, end_date=end_date)

        # TODO initialize the auto refresh

    def _fetch_values(self, PV, start_date, end_date=None):
        return self._archiver.getWaveform(PV, start_date=start_date, end_date=end_date)

