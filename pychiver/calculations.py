"""
ESS 2021
Authors:
    A.Gorzawski <arek.gorzawski@ess.eu>
"""
import warnings
import numpy as np


class InterpolationStrategy:

    def __init__(self, baseXs):
        self.baseTs = baseXs
        if len(baseXs) < 2:
            raise ValueError('Cannot initialize with too short {}<2 time base '.format(len(baseXs)))

    def getValues(self, xs, ys) -> list:
        raise NotImplementedError('Abstract implementation called, use concrete ones.')


class LinearInterpolationStrategy(InterpolationStrategy):

    def getValues(self, xs: list, ys: list) -> list:
        """
        Return new values that are aligned with the base Time Stamps
        :param xs:
        :param ys:
        :return:
        """
        if self.baseTs[0] < xs[0]:
            warnings.warn('Adjusting at lower end while interpolating. Requested time {}, the lowest available {}.'.format(self.baseTs[0], xs[0]))
        if self.baseTs[-1] > xs[-1]:
            warnings.warn('Adjusting at higher end while interpolating. Requested time {},the highest available {}.'.format(self.baseTs[-1], xs[-1]))
        return np.interp(self.baseTs, xs, ys)