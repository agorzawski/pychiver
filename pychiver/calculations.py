"""
ESS 2021
Authors:
    A.Gorzawski <arek.gorzawski@ess.eu>
"""


class InterpolationStrategy:

    def __init__(self, baseXs):
        self.baseTs = baseXs

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
        pass