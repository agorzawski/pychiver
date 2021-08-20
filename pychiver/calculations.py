"""
ESS 2021
Authors:
    A.Gorzawski <arek.gorzawski@ess.eu>
"""
import warnings
from enum import Enum

import numpy as np
import pandas as pd


class InterpolationStrategy:

    def __init__(self, baseXs):
        self.baseTs = baseXs
        if len(baseXs) < 2:
            raise ValueError('Cannot initialize with too short {}<2 time base '.format(len(baseXs)))

    def getValues(self, xs, ys) -> list:
        raise NotImplementedError('Abstract implementation called for InterpolationStrategy,\
                                    use concrete ones.')


class LinearInterpolationStrategy(InterpolationStrategy):

    def getValues(self, xs: list, ys: list) -> list:
        """
        Return new values that are aligned with the base Time Stamps
        :param xs:
        :param ys:
        :return:
        """
        if self.baseTs[0] < xs[0]:
            warnings.warn(
                'Adjusting at lower end while interpolating. Requested time {}, the lowest available {}.'.format(
                    self.baseTs[0], xs[0]))
        if self.baseTs[-1] > xs[-1]:
            warnings.warn(
                'Adjusting at higher end while interpolating. Requested time {},the highest available {}.'.format(
                    self.baseTs[-1], xs[-1]))
        return np.interp(self.baseTs, xs, ys)


class LastAcquiredValueInterpolationStrategy(InterpolationStrategy):

    def getValues(self, xs: list, ys: list) -> list:
        """
        Return new values that are aligned with the base Time Stamps, and represent the closest (earlier) value
        :param xs:
        :param ys:
        :return:
        """
        if len(xs) != len(ys):
            raise ValueError('Provided arrays not of the same length!')
        idx = np.searchsorted(xs, self.baseTs, side='right')
        return np.array(ys)[np.maximum(idx - 1, 0)]


def alignDataFrames(dict_of_datasets,
                    time_base=None,
                    InterpolationStrategyImpl=None,
                    time_column='time', value_columns=("val",), verbose=False) -> pd.DataFrame:
    """
    For a given dict of DataFrames (dict of 'Data Label' -> DataFrame), the data alignment is performed for the
    provided data sets values (according to provided value columns) and the provided new time base
    (first dataset's time or the external provided time base) using of provided interpolation strategy
    (default is LinearInterpolationStrategy)

    :param dict_of_datasets:
    :param time_base: default None,
    :param InterpolationStrategyImpl:
    :param time_column: default 'time'
    :param value_columns: default 'val'
    :param verbose: default False, prints out the progress on the computation
    :return: pandas DataFrame with one time column and value columns for each data label
    """
    if InterpolationStrategyImpl is None:
        raise ValueError('Cannot align data sets without a valid InterpolationStrategy')

    if not isinstance(dict_of_datasets, dict):
        raise ValueError('Provided data sets should be in dict, ie. {\'PV1\':df_1,\'PV2\':df_2,}')

    numberOfValidDfs = 0
    dfToSkip = []
    for df_name in dict_of_datasets.keys():
        one_df = dict_of_datasets[df_name]
        if one_df.empty:
            dfToSkip.append(df_name)
            warnings.warn('Provided an empty dataframe for \'{}\', skipping it for the interpolation!'.format(df_name))
            continue
        if time_column not in one_df.columns:
            raise ValueError('One of the dataframes does not have \'{}\' column'.format(time_column))
        for one_val_column in value_columns:
            if one_val_column not in one_df.columns:
                raise ValueError('One of the dataframes does not have \'{}\' column'.format(one_val_column))

        numberOfValidDfs += 1

    if numberOfValidDfs < 2 and time_base is None:
        raise ValueError('Only one valid DataFrame provided with no external time_base! Fix your data input.')

    newDF_columns = [time_column]
    for one_PV in dict_of_datasets.keys():
        if one_PV in dfToSkip:
            continue
        for one_val_column in value_columns:
            newDF_columns.append(one_PV + ':' + one_val_column)
    newDF_values = []
    firstPV = list(dict_of_datasets.keys())[0]

    if time_base is None:
        isImpl = InterpolationStrategyImpl(dict_of_datasets[firstPV][time_column].to_numpy())
        newDF_values.append(dict_of_datasets[firstPV][time_column].to_numpy())
        if verbose:
            print('First PV used as a time base: ', firstPV)
    else:
        isImpl = InterpolationStrategyImpl(time_base)
        newDF_values.append(time_base)
        if verbose:
            print('External time base used.')

    for one_PV in dict_of_datasets.keys():
        if one_PV in dfToSkip:
            continue
        for one_val_column in value_columns:
            if verbose:
                print("Interpolating for {}:{}".format(one_PV, one_val_column))
            x = isImpl.getValues(dict_of_datasets[one_PV][time_column].to_numpy(),
                                 dict_of_datasets[one_PV][one_val_column].to_numpy())
            newDF_values.append(x)
    if verbose:
        print('Alignment completed!')

    returnDF = pd.DataFrame(np.transpose(np.array(newDF_values)), columns=newDF_columns)
    returnDF['time'] = pd.to_datetime(returnDF[time_column], unit='s')
    return returnDF


def calculateMovingAverage(dataset, window=10,
                           time_column='secs_nanos', value_columns=('val',), verbose=False):
    """
    Modifies the the provided data set, by adding extra columns for mean time and mean values.

    :param dataset: data set to update
    :param value_columns:
    :param time_column:
    :param window: default 10s
    :param verbose:
    :return: None
    """
    df = pd.DataFrame()
    if dataset.empty:
        warnings.warn('Cannot apply moving average on an empty dataframe, skipping.')
        return df
    df[time_column] = dataset[time_column]
    df['mean_time'] = pd.to_datetime((dataset[time_column]).rolling(window=window).mean(), unit='s')
    for one_value_column in value_columns:
        if verbose: print("Column \'{}\' applied with {}s moving average".format(one_value_column, window))
        df['mean_' + one_value_column] = dataset[one_value_column].rolling(window=window).mean()
    df.dropna(inplace=True)
    return df


def returnMethods():
    """
    TODO Ported from spec2d
    :return:
    """
    return ['None', 'FFT (Abs)', 'FFT (Img)', 'FFT (Re)', 'FFT (Ang)', 'iFFT (Abs)', 'iFFT (Img)', 'iFFT (Re)',
            'iFFT (Ang)']


def get_fft(fftMethodIndex, array_in):
    """
    TODO Ported from spec2d
    :return:
    """
    currentText = returnMethods()[fftMethodIndex]
    if currentText == 'FFT (Abs)':
        return np.abs(np.fft.fft(array_in))
    elif currentText == 'FFT (Img)':
        return np.fft.fft(array_in).imag
    elif currentText == 'FFT (Re)':
        return np.fft.fft(array_in).real
    elif currentText == 'FFT (Ang)':
        return np.angle(np.fft.fft(array_in))
    elif currentText == 'iFFT (Abs)':
        return np.abs(np.fft.ifft(array_in))
    elif currentText == 'iFFT (Img)':
        return np.fft.ifft(array_in).imag
    elif currentText == 'iFFT (Re)':
        return np.fft.ifft(array_in).real
    elif currentText == 'iFFT (Ang)':
        return np.angle(np.fft.ifft(array_in))
    else:
        return array_in


class Method(Enum):
    AND = 0
    OR = 1
    XOR = 2


class Edge(Enum):
    RISING = 0
    FALLING = 1
    ANY = -1


def findCloseTimestamps(dfs,
                        edge_to_use=Edge.RISING,
                        tolerance_in_seconds=1,
                        timeColumn='secs_nanos',
                        valueColumn='val',
                        verbose=False):
    newTs = []
    for pv in dfs.keys():
        oneDf = dfs[pv]
        if not oneDf[valueColumn].between(0, 1, inclusive="both").any():
            raise ValueError('It seems that your boolean data for {} has values outside of 0 and 1... cannot')
        toConsider = oneDf.loc[oneDf[valueColumn] != edge_to_use.value]
        if verbose:
            print('---------{}-----------'.format(pv))
            print(oneDf[timeColumn].values)
            print(toConsider)
        newTs.extend(toConsider[timeColumn].values)

    allTimeStamps = np.array(newTs)
    closeOnes = allTimeStamps[:-1] - allTimeStamps[1:]
    closeOnes.sort()
    indexes = np.where(np.abs(closeOnes) < tolerance_in_seconds)
    if verbose:
        print(indexes)
        print(allTimeStamps[indexes])
    return allTimeStamps[indexes]


def compareTwoBooleanArrays(array1, array2, method=Method.AND):
    """

    :param array1:
    :param array2:
    :param method:
    :return:
    """
    if not isinstance(method, Method):
        raise ValueError('The method you provided is not an instance of Method in this package!')
    if method == Method.AND:
        return np.bitwise_and(array1, array2)
    if method == Method.OR:
        return np.bitwise_or(array1, array2)
    if method == Method.XOR:
        return np.bitwise_xor(array1, array2)
