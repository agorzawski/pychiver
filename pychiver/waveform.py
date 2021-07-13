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


class Collector(ABC):
    """
    An abstract class for waveform collectors
    """
    def getLastWaveForm(self, timestamp=None, last=1) -> pandas.DataFrame:
        pass

    def getAllWaveForms(self) -> pandas.DataFrame:
        pass

    def null_callback(self, **kwargs):
        pass


class PVWaveformCollector(Collector):

    def __init__(self, PV:str, callback=None, callback_delay_in_seconds=1, data_buffer=3*60):
        """
        Initialises PV waveform data collector. It uses camonitor from pyepics.

        :param PV: name of the pv
        :param callback: an external function to call
        :param callback_delay_in_seconds: a delay at which to call an external function, default 1s
        :param data_buffer: default 180s,
        """
        if not isinstance(PV, str):
            raise ValueError('Use one PVWaveFormCollector per one PV')
        self._PV = PV
        if callback is None:
            warnings.warn('You have not defined the callback function! dev>null will be used.')
            callback = self.null_callback
        self._callback = callback
        self._callback_delay = timedelta(seconds=callback_delay_in_seconds)
        self._callback_last_call = datetime.now()
        self._data_buffer = data_buffer
        self._dataframe = pandas.DataFrame(columns={'time', 'pv', 'val'})
        print('Starting ca monitor')
        epics.camonitor(self._PV, callback=self._execute_callback, connection_timeout=1)
        print('done!')

    def _execute_callback(self, pvname=None, value=None, char_value=None, **kwargs):
        timestamp = datetime.fromtimestamp(kwargs["timestamp"])
        # append new
        self._dataframe = self._dataframe.append({'time': timestamp, 'pv': pvname, 'val': value}, ignore_index=True)
        # drop older than collector's buffer
        oldest_to_keep = timestamp - timedelta(seconds=self._data_buffer)
        self._dataframe.drop(self._dataframe[self._dataframe['time'] < oldest_to_keep].index, inplace=True)
        checkTime = datetime.now()
        if checkTime > self._callback_last_call + self._callback_delay:
            self._callback_last_call = checkTime
            self._callback(PV=self._PV, dataframe=self._dataframe, lastCheck=checkTime)
        else:
            pass

    def getLastWaveForm(self, timestamp=None, last=1) -> pandas.DataFrame:
        if timestamp is None:
            return self._dataframe.iloc[[-1]]
        else:
            # TODO use last available value as interpolation strategy
            raise NotImplementedError('Only last acquisition available for now, with timestamp=None.')

    def getAllWaveForms(self) -> pandas.DataFrame:
        return self._dataframe  # TODO consider deep copy


class ArchiverCollector(Collector):
    pass


