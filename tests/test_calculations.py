import unittest
from pychiver.calculations import *

SIMPLE_TIMES = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
SIMPLE_VALUES = [i * i for i in SIMPLE_TIMES]

NEW_TIME_BASE_CORRECT = [1, 3, 4.5, 7.66, 10 ]
NEW_VALUES_CORRECT_TIME_BASE = [1 , 9., 20.5, 58.9, 100.]

NEW_TIME_BASE_INCORRECT = [-1, 3, 4.5, 7.66, 14 ]
NEW_VALUES_INCORRECT_TIME_BASE = [1., 9., 20.5, 58.9, 100.]


class TestLinearInterpolation(unittest.TestCase):

    def test_wrong_init(self):
        with self.assertRaises(ValueError):
            lis = LinearInterpolationStrategy(baseXs=[1])

    def test_with_the_same_base(self):
        lis = LinearInterpolationStrategy(baseXs=SIMPLE_TIMES)
        result = lis.getValues(SIMPLE_TIMES, SIMPLE_VALUES)
        self._compare_two_arrays(result, SIMPLE_VALUES)

    def test_the_correct_base(self):
        lis = LinearInterpolationStrategy(baseXs=NEW_TIME_BASE_CORRECT)
        result = lis.getValues(SIMPLE_TIMES, SIMPLE_VALUES)
        self._compare_two_arrays(result, NEW_VALUES_CORRECT_TIME_BASE)

    def test_with_the_incorrect_base(self):
        lis = LinearInterpolationStrategy(baseXs=NEW_TIME_BASE_INCORRECT)
        result = lis.getValues(SIMPLE_TIMES, SIMPLE_VALUES)
        print(result)
        self._compare_two_arrays(result, NEW_VALUES_INCORRECT_TIME_BASE)

    def _compare_two_arrays(self, array1, array2):
        self.assertEqual(len(array1), len(array2))
        for i in range(len(array1)):
            self.assertAlmostEqual(array1[i], array2[i], places=2)


if __name__ == '__main__':
    unittest.main()
