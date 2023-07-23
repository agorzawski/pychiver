import unittest

from pychiver.sardomain import *

SIMPLE_JSON_EXAMPLE = {
    "uniqueId": 666,
    "name": "NumberOfTheBeast",
    "nodeType": "THE PIT",
}
JSON_FOR_CONFIG_PVS = [
    {
        "snapshotId": 3076,
        "configPv": {"pvName": "Lucifer PV", "readbackPvName":'blah'},
        "value": {
            "type": {"name": "VDoubleArray", "version": 1},
            "value": -666,
            "alarm": {"severity": "NONE", "status": "NONE", "name": "NONE"},
            "time": {"unixSec": 1623165540, "nanoSec": 386023508},
            "display": {"units": ""},
        },
    }
]


class TestSARItems(unittest.TestCase):
    def test_incorrect_init_folder(self):
        with self.assertRaises(ValueError):
            SARFolder(**SIMPLE_JSON_EXAMPLE)

    def test_correct_init_folder(self):
        SARFolder(**{**SIMPLE_JSON_EXAMPLE, "fullPath": "Hell/Level1"})

    def test_incorrect_init_snapshot(self):
        with self.assertRaises(ValueError):
            SARSnapshot(**SIMPLE_JSON_EXAMPLE)

    def test_correct_init_snapshot(self):
        SARSnapshot(**{**SIMPLE_JSON_EXAMPLE, "snapshotItems": JSON_FOR_CONFIG_PVS})

    def test_correct_snapshot_build_dataframe(self):
        ll = SARSnapshot(**{**SIMPLE_JSON_EXAMPLE, "snapshotItems": JSON_FOR_CONFIG_PVS})
        print(ll.getStoredValues())

    def test_incorrect_init_configpv(self):
        with self.assertRaises(ValueError):
            SARConfigPV()

    def test_correct_init_configpv(self):
        SARConfigPV(**JSON_FOR_CONFIG_PVS[0])
