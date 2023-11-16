import unittest
import sys
import os
sys.path.append(os.path.abspath('..'))
from pychiver.calculations import *

SIMPLE_TIMES = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
SIMPLE_VALUES = [i * i for i in SIMPLE_TIMES]

NEW_TIME_BASE_CORRECT = [1, 3, 4.5, 7.66, 10]
NEW_VALUES_CORRECT_TIME_BASE = [1, 9.0, 20.5, 58.9, 100.0]
NEW_VALUES_CORRECT_TIME_BASE_LAST_ACQ = [1, 9, 16, 49, 100]

NEW_TIME_BASE_INCORRECT = [-1, 3, 4.5, 7.66, 14]
NEW_VALUES_INCORRECT_TIME_BASE = [1.0, 9.0, 20.5, 58.9, 100.0]
NEW_VALUES_INCORRECT_TIME_BASE_LAST_ACQ = [1, 9, 16, 49, 100]

DF_COLUMNS = ["time", "val", "some_other"]
DF_1 = pd.DataFrame(np.array([[1.0, 2, 3], [2.0, 5, 6], [3.0, 8, 9], [4.0, 7, 3], [5.0, 4, 2]]), columns=DF_COLUMNS)
DF_1_VAL_MOVING_AVERAGE_2_s = [3.5, 6.5, 7.5, 5.5]

DF_2 = pd.DataFrame(np.array([[1.0, 2, 3], [2.5, 5, 6], [3.1, 8, 9], [4.1, 8, 2], [4.9, 6, 3]]), columns=DF_COLUMNS)

DF_3 = pd.DataFrame(np.array([[1.0, 2, 3], [1.0, 1.0, 1.0], [5, 5, 5], [4.1, 8, 2], [4.9, 4.9, 4.9]]), columns=DF_COLUMNS)

DF_2_VAL_FOR_DF_1_TIME = [
    2.0,
    4.0,
    7.5,
    8.0,
    6.0,
]

DF_2_VAL_FOR_DF_1_TIME_INTER_LAST = [
    2.0,
    2.0,
    5.0,
    8.0,
    6.0
]


EXTERNAL_TIME_BASE = [1.1, 1.2, 1.3, 2.4, 3.5, 3.7, 4.2]


DF_1_VAL_FOR_EXTERNAL_TIME_BASE = [2.3, 2.6, 2.9, 6.2, 7.5, 7.3, 6.4]
DF_2_VAL_FOR_EXTERNAL_TIME_BASE = [2.2, 2.4, 2.6, 4.8, 8.0, 8.0, 7.75]

DF_1_VAL_FOR_EXTERNAL_TIME_BASE_LAST = [2.0, 2.0, 2.0, 5.0, 8.0, 8.0, 7.0]
DF_2_VAL_FOR_EXTERNAL_TIME_BASE_LAST = [2.0, 2.0, 2.0, 2.0, 8.0, 8.0, 8.0]

DF_RAND_COLUMNS = pd.DataFrame(np.array([[1, 2, 3], [2, 5, 6], [3, 8, 9], [4, 8, 9]]), columns=["some1", "value2", "another"])

DF_BOOL_TS = [1, 2, 3, 4, 5, 6]
DF_BOOL_1 = [1, 0, 1, 0, 1, 0]
DF_BOOL_2 = [0, 1, 0, 1, 0, 1]
DF_BOOL_TEST_1OR2 = [1, 1, 1, 1, 1, 1]
DF_BOOL_TEST_1AND2 = [0, 0, 0, 0, 0, 0]

DF_BOOL_3 = [0, 1, 1, 1, 1, 0]
DF_BOOL_TEST_1OR3 = [1, 1, 1, 1, 1, 0]
DF_BOOL_TEST_1AND3 = [0, 0, 1, 0, 1, 0]
DF_BOOL_TEST_1XOR3 = [1, 1, 0, 1, 0, 0]


class TestLinearInterpolation(unittest.TestCase):
    def test_wrong_init(self):
        with self.assertRaises(ValueError):
            LinearInterpolationStrategy(baseXs=[1])

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
        self._compare_two_arrays(result, NEW_VALUES_INCORRECT_TIME_BASE)

    def _compare_two_arrays(self, array1, array2):
        self.assertEqual(len(array1), len(array2))
        for i in range(len(array1)):
            self.assertAlmostEqual(array1[i], array2[i], places=2)


class TestLastValueInterpolation(unittest.TestCase):
    def test_wrong_init(self):
        with self.assertRaises(ValueError):
            LastAcquiredValueInterpolationStrategy(baseXs=[1])

    def test_the_correct_base(self):
        lis = LastAcquiredValueInterpolationStrategy(baseXs=NEW_TIME_BASE_CORRECT)
        result = lis.getValues(SIMPLE_TIMES, SIMPLE_VALUES)
        self._compare_two_arrays(result, NEW_VALUES_CORRECT_TIME_BASE_LAST_ACQ)

    def test_with_the_incorrect_base(self):
        lis = LastAcquiredValueInterpolationStrategy(baseXs=NEW_TIME_BASE_INCORRECT)
        result = lis.getValues(SIMPLE_TIMES, SIMPLE_VALUES)
        self._compare_two_arrays(result, NEW_VALUES_INCORRECT_TIME_BASE_LAST_ACQ)

    def _compare_two_arrays(self, array1, array2):
        self.assertEqual(len(array1), len(array2))
        for i in range(len(array1)):
            self.assertAlmostEqual(array1[i], array2[i], places=2)


class TestDataAlign(unittest.TestCase):
    def test_wrong_init_no_interpolation(self):
        with self.assertRaises(ValueError):
            alignDataFrames({"PV1": DF_1, "PV2": DF_2})

    def test_wrong_init_no_interpolation_list(self):
        with self.assertRaises(ValueError):
            alignDataFrames({"PV1": DF_1, "PV2": DF_2}, InterpolationStrategyImpl=InterpolationStrategy)

    def test_wrong_init_mismatch_unique_PVS_and_interpolation_strategies(self):
        with self.assertRaises(ValueError):
            alignDataFrames({"PV1": DF_1, "PV1": DF_1, "PV2": DF_2}, InterpolationStrategyImpl=[InterpolationStrategy]*3)

        with self.assertRaises(ValueError):
            alignDataFrames({"PV1": DF_1, "PV2": DF_2}, InterpolationStrategyImpl=[InterpolationStrategy]*3)

        with self.assertRaises(ValueError):
            alignDataFrames({"PV1": DF_1, "PV2": DF_2, "PV3": DF_3}, InterpolationStrategyImpl=[InterpolationStrategy]*2)

    def test_wrong_init_wrong_amount_dfs(self):
        with self.assertRaises(ValueError):
            alignDataFrames({"PV1": DF_1}, InterpolationStrategyImpl=[InterpolationStrategy])

    def test_wrong_init_wrong_columns_in_df(self):
        with self.assertRaises(ValueError):
            alignDataFrames({"PV1": DF_1, "PV2": DF_RAND_COLUMNS}, InterpolationStrategyImpl=[InterpolationStrategy]*2)

    def test_align_with_first_df_time(self):
        result1 = alignDataFrames({"PV1": DF_1, "PV2": DF_2}, InterpolationStrategyImpl=[LinearInterpolationStrategy]*2)
        self._compare_two_arrays(DF_2_VAL_FOR_DF_1_TIME, result1["PV2:val"].to_numpy())

        result2 = alignDataFrames({"PV1": DF_1, "PV2": DF_2},
                                      InterpolationStrategyImpl=[LastAcquiredValueInterpolationStrategy, LinearInterpolationStrategy])
        self._compare_two_arrays(DF_2_VAL_FOR_DF_1_TIME, result2["PV2:val"].to_numpy())

        result3 = alignDataFrames({"PV1": DF_1, "PV2": DF_2},
                                      InterpolationStrategyImpl=[LinearInterpolationStrategy, LastAcquiredValueInterpolationStrategy])
        self._compare_two_arrays(DF_2_VAL_FOR_DF_1_TIME_INTER_LAST, result3["PV2:val"].to_numpy())

    def test_align_with_external_time_base(self):
        result1 = alignDataFrames(
            {"PV1": DF_1, "PV2": DF_2},
            time_base=EXTERNAL_TIME_BASE,
            value_columns=("val", "some_other"),
            InterpolationStrategyImpl=[LinearInterpolationStrategy]*2
        )
        self._compare_two_arrays(DF_1_VAL_FOR_EXTERNAL_TIME_BASE, result1["PV1:val"].to_numpy())
        self._compare_two_arrays(DF_2_VAL_FOR_EXTERNAL_TIME_BASE, result1["PV2:val"].to_numpy())

        result2 = alignDataFrames(
            {"PV1": DF_1, "PV2": DF_2},
            time_base=EXTERNAL_TIME_BASE,
            value_columns=("val", "some_other"),
            InterpolationStrategyImpl=[LastAcquiredValueInterpolationStrategy] * 2
        )
        self._compare_two_arrays(DF_1_VAL_FOR_EXTERNAL_TIME_BASE_LAST, result2["PV1:val"].to_numpy())
        self._compare_two_arrays(DF_2_VAL_FOR_EXTERNAL_TIME_BASE_LAST, result2["PV2:val"].to_numpy())

        result3 = alignDataFrames(
            {"PV1": DF_1, "PV2": DF_2},
            time_base=EXTERNAL_TIME_BASE,
            value_columns=("val", "some_other"),
            InterpolationStrategyImpl=[LinearInterpolationStrategy, LastAcquiredValueInterpolationStrategy]
        )
        self._compare_two_arrays(DF_1_VAL_FOR_EXTERNAL_TIME_BASE, result3["PV1:val"].to_numpy())
        self._compare_two_arrays(DF_2_VAL_FOR_EXTERNAL_TIME_BASE_LAST, result3["PV2:val"].to_numpy())

        result4 = alignDataFrames(
            {"PV1": DF_1, "PV2": DF_2},
            time_base=EXTERNAL_TIME_BASE,
            value_columns=("val", "some_other"),
            InterpolationStrategyImpl=[LastAcquiredValueInterpolationStrategy, LinearInterpolationStrategy]
        )
        self._compare_two_arrays(DF_1_VAL_FOR_EXTERNAL_TIME_BASE_LAST, result4["PV1:val"].to_numpy())
        self._compare_two_arrays(DF_2_VAL_FOR_EXTERNAL_TIME_BASE, result4["PV2:val"].to_numpy())

    def test_align_one_df_with_external_time_base(self):
        result1 = alignDataFrames(
            {"PV1": DF_1},
            time_base=EXTERNAL_TIME_BASE,
            value_columns=("val", "some_other"),
            InterpolationStrategyImpl=[LinearInterpolationStrategy]
        )
        self._compare_two_arrays(DF_1_VAL_FOR_EXTERNAL_TIME_BASE, result1["PV1:val"].to_numpy())

        result2 = alignDataFrames(
            {"PV1": DF_1},
            time_base=EXTERNAL_TIME_BASE,
            value_columns=("val", "some_other"),
            InterpolationStrategyImpl=[LastAcquiredValueInterpolationStrategy]
        )
        self._compare_two_arrays(DF_1_VAL_FOR_EXTERNAL_TIME_BASE_LAST, result2["PV1:val"].to_numpy())

    def _compare_two_arrays(self, array1, array2):
        self.assertEqual(len(array1), len(array2))
        for i in range(len(array1)):
            self.assertAlmostEqual(array1[i], array2[i], places=2)


class TestMovingAverage(unittest.TestCase):
    def test_simple(self):
        df = calculateMovingAverage(DF_1, window=2, time_column="time")
        self._compare_two_arrays(df["mean_val"].to_numpy(), DF_1_VAL_MOVING_AVERAGE_2_s)

    def _compare_two_arrays(self, array1, array2):
        self.assertEqual(len(array1), len(array2))
        for i in range(len(array1)):
            self.assertAlmostEqual(array1[i], array2[i], places=2)


class TestBooleanActions(unittest.TestCase):
    def test_when_one_with_wrong_method_class(self):
        with self.assertRaises(ValueError):
            compareTwoBooleanArrays(DF_BOOL_1, DF_BOOL_2, method=True)

    def test_when_one_with_another_AND(self):
        result = compareTwoBooleanArrays(DF_BOOL_1, DF_BOOL_2, method=Method.AND)
        self._compare_two_arrays(result, DF_BOOL_TEST_1AND2)
        result = compareTwoBooleanArrays(DF_BOOL_1, DF_BOOL_3, method=Method.AND)
        self._compare_two_arrays(result, DF_BOOL_TEST_1AND3)

    def test_when_one_with_another_OR(self):
        result = compareTwoBooleanArrays(DF_BOOL_1, DF_BOOL_2, method=Method.OR)
        self._compare_two_arrays(result, DF_BOOL_TEST_1OR2)
        result = compareTwoBooleanArrays(DF_BOOL_1, DF_BOOL_3, method=Method.OR)
        self._compare_two_arrays(result, DF_BOOL_TEST_1OR3)

    def test_when_one_with_another_XOR(self):
        result = compareTwoBooleanArrays(DF_BOOL_1, DF_BOOL_3, method=Method.XOR)
        self._compare_two_arrays(result, DF_BOOL_TEST_1XOR3)

    def _compare_two_arrays(self, array1, array2):
        self.assertEqual(len(array1), len(array2))
        for i in range(len(array1)):
            self.assertAlmostEqual(array1[i], array2[i], places=2)


if __name__ == "__main__":
    unittest.main()
