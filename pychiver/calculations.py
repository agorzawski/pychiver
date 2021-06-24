"""
ESS 2021
Authors:
    A.Gorzawski <arek.gorzawski@ess.eu>
"""
import warnings
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

    if len(dict_of_datasets.keys()) < 2 and time_base is None:
        raise ValueError('Only one DataFrame provided with no external time_base.')

    for one_df in dict_of_datasets.values():
        if time_column not in one_df.columns:
            raise ValueError('One of the dataframes does not have \'{}\' column'.format(time_column))
        for one_val_column in value_columns:
            if one_val_column not in one_df.columns:
                raise ValueError('One of the dataframes does not have \'{}\' column'.format(one_val_column))

    newDF_columns = [time_column]
    for one_PV in dict_of_datasets.keys():
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
    df[time_column] = dataset[time_column]
    df['mean_time'] = pd.to_datetime((dataset[time_column]).rolling(window=window).mean(), unit='s')
    for one_value_column in value_columns:
        if verbose: print("Column \'{}\' applied with {}s moving average".format(one_value_column, window))
        df['mean_'+one_value_column] = dataset[one_value_column].rolling(window=window).mean()
    df.dropna(inplace=True)
    return df
