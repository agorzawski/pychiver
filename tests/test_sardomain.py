import unittest

from pychiver.sardomain import *

SIMPLE_JSON_EXAMPLE_FOR_ANY_SAR_OBJECT = {
    "uniqueId": 666,
    "name": "NumberOfTheBeast",
    "nodeType": "THE PIT",
}

JSON_SIMPLE_CONFIG = {"pvName": "Lucifer PV", "readbackPvName": "blah", "readonly": False}
JSON_SIMPLE_SNAPSHOT_VALUE = {
            "type": {"name": "VDoubleArray", "version": 1},
            "value": -666,
            "alarm": {"severity": "NONE", "status": "NONE", "name": "NONE"},
            "time": {"unixSec": 1623165540, "nanoSec": 386023508},
            "display": {"units": ""},
        }

JSON_FOR_COMPLETE_SNAPSHOT_VALUE = [
    {
        "configPv": JSON_SIMPLE_CONFIG,
        "value": JSON_SIMPLE_SNAPSHOT_VALUE,
    }
]


class TestSARItems(unittest.TestCase):
    def test_incorrect_init_folder(self):
        with self.assertRaises(ValueError):
            SARFolder(**SIMPLE_JSON_EXAMPLE_FOR_ANY_SAR_OBJECT)

    def test_correct_init_folder(self):
        SARFolder(**{**SIMPLE_JSON_EXAMPLE_FOR_ANY_SAR_OBJECT, "fullPath": "Hell/Level1"})

    def test_incorrect_init_snapshot(self):
        with self.assertRaises(ValueError):
            SARSnapshot(**SIMPLE_JSON_EXAMPLE_FOR_ANY_SAR_OBJECT)

    def test_correct_init_snapshot(self):
        SARSnapshot(**{**SIMPLE_JSON_EXAMPLE_FOR_ANY_SAR_OBJECT, "snapshotItems": JSON_FOR_COMPLETE_SNAPSHOT_VALUE})

    def test_correct_snapshot_build_dataframe(self):
        ll = SARSnapshot(**{**SIMPLE_JSON_EXAMPLE_FOR_ANY_SAR_OBJECT, "snapshotItems": JSON_FOR_COMPLETE_SNAPSHOT_VALUE})
        print(ll.getStoredValues())

    def test_incorrect_init_configpv(self):
        with self.assertRaises(ValueError):
            SARConfigPV()

    def test_correct_init_configpv(self):
        SARConfigPV(**JSON_FOR_COMPLETE_SNAPSHOT_VALUE[0])

    def test_correct_init_configpv_2(self):
        SARConfigPV(**JSON_SIMPLE_CONFIG)

    def test_correct_init_snapshotitem(self):
        SARSnapshotItem(**JSON_FOR_COMPLETE_SNAPSHOT_VALUE[0])