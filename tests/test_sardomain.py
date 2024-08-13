import unittest

from pychiver.sardomain import *

SIMPLE_JSON_EXAMPLE_FOR_ANY_SAR_OBJECT = {
    "uniqueId": 666,
    "name": "NumberOfTheBeast",
    "nodeType": "THE PIT",
}

SIMPLE_JSON_EXAMPLE_FOR_ANY_SAR_OBJECT_NB2 = {
    "uniqueId": -666,
    "name": "NumberOfTheBeast Square",
    "nodeType": "THE PIT",
}

PV_NAME = "Lucifer PV"
PV_VALUE = -666
PV_READBACK_NAME = "Belzebub PV"
PV_READBACK_VALUE = -999

PV_2_NAME = "XXX"
PV_2_READBACK_NAME = "YYY"

JSON_SIMPLE_CONFIG = {"pvName": PV_NAME, "readbackPvName": None, "readonly": False}
JSON_SIMPLE_SNAPSHOT_VALUE = {
    "type": {"name": "VDouble", "version": 1},
    "value": PV_VALUE,
    "alarm": {"severity": "NONE", "status": "NONE", "name": "NONE"},
    "time": {"unixSec": 1623165540, "nanoSec": 386023508},
    "display": {"units": "mA"},
}

JSON_SIMPLE_PLUS_READBACK_CONFIG = {"pvName": PV_NAME, "readbackPvName": PV_READBACK_NAME, "readonly": False}
JSON_SIMPLE_READBACK_SNAPSHOT_VALUE = {
    "type": {"name": "VDouble", "version": 1},
    "value": PV_READBACK_VALUE,
    "alarm": {"severity": "NONE", "status": "NONE", "name": "NONE"},
    "time": {"unixSec": 1623165540, "nanoSec": 386023508},
    "display": {"units": "kW"},
}


JSON_FOR_COMPLETE_SNAPSHOT_VALUE = [
    {
        "configPv": JSON_SIMPLE_CONFIG,
        "value": JSON_SIMPLE_SNAPSHOT_VALUE,
    }
]

JSON_FOR_COMPLETE_SNAPSHOT_VALUE_WITH_READBACK = [
    {"configPv": JSON_SIMPLE_PLUS_READBACK_CONFIG, "value": JSON_SIMPLE_SNAPSHOT_VALUE, "readbackValue": JSON_SIMPLE_READBACK_SNAPSHOT_VALUE}
]

JSON_SIMPLE_PLUS_READBACK_CONFIG_2 = {"pvName": PV_2_NAME, "readbackPvName": PV_2_READBACK_NAME, "readonly": False}
JSON_FOR_COMPLETE_SNAPSHOT_VALUE_FEW_PVS_ONE_WITH_READBACK = [
    {"configPv": JSON_SIMPLE_PLUS_READBACK_CONFIG_2, "value": JSON_SIMPLE_SNAPSHOT_VALUE, "readbackValue": JSON_SIMPLE_READBACK_SNAPSHOT_VALUE},
    {
        "configPv": JSON_SIMPLE_CONFIG,
        "value": JSON_SIMPLE_SNAPSHOT_VALUE,
    },
]


class TestSARItems(unittest.TestCase):
    def test_incorrect_init_folder(self):
        with self.assertRaises(ValueError):
            SARFolder(**SIMPLE_JSON_EXAMPLE_FOR_ANY_SAR_OBJECT)

    def test_correct_init_folder(self):
        SARFolder(**{**SIMPLE_JSON_EXAMPLE_FOR_ANY_SAR_OBJECT, "fullPath": "Hell/Level1"})

    def test_incorrect_init_configpv(self):
        with self.assertRaises(ValueError):
            SARConfigPV()

    # def test_correct_init_configpv(self):
    #     a = SARConfigPV(**JSON_FOR_COMPLETE_SNAPSHOT_VALUE[0])
    #     self.assertEqual(a.pvName, PV_NAME)

    def test_correct_init_configpv_2(self):
        a = SARConfigPV(**JSON_SIMPLE_CONFIG)
        self.assertEqual(a.pvName, PV_NAME)

    def test_correct_init_snapshotitem(self):
        a = SARSnapshotItem(**JSON_FOR_COMPLETE_SNAPSHOT_VALUE[0])
        self.assertEqual(a.pvValue, PV_VALUE)

    def test_correct_init_snapshotitem_with_readback(self):
        a = SARSnapshotItem(**JSON_FOR_COMPLETE_SNAPSHOT_VALUE_WITH_READBACK[0])
        self.assertEqual(a.readbackPvValue, PV_READBACK_VALUE)
        self.assertEqual(a.pvValue, PV_VALUE)


class TestSARSnapshotsDetailed(unittest.TestCase):
    def test_correct_init_snapshot(self):
        a = SARSnapshot(**{**SIMPLE_JSON_EXAMPLE_FOR_ANY_SAR_OBJECT, "snapshotItems": JSON_FOR_COMPLETE_SNAPSHOT_VALUE})
        self.assertFalse(a.dirty)

    def test_incorrect_init_snapshot(self):
        with self.assertRaises(ValueError):
            SARSnapshot(**SIMPLE_JSON_EXAMPLE_FOR_ANY_SAR_OBJECT)

    def test_correct_dirty_init_snapshot(self):
        a = SARSnapshot(**{**SIMPLE_JSON_EXAMPLE_FOR_ANY_SAR_OBJECT, "snapshotItems": JSON_FOR_COMPLETE_SNAPSHOT_VALUE, "dirty": True})
        self.assertTrue(a.dirty)

    def test_correct_snapshot_build_dataframe(self):
        SARSnapshot(**{**SIMPLE_JSON_EXAMPLE_FOR_ANY_SAR_OBJECT, "snapshotItems": JSON_FOR_COMPLETE_SNAPSHOT_VALUE})

    def test_correct_init_snapshot_with_readbacks(self):
        a = SARSnapshot(**{**SIMPLE_JSON_EXAMPLE_FOR_ANY_SAR_OBJECT, "snapshotItems": JSON_FOR_COMPLETE_SNAPSHOT_VALUE_WITH_READBACK})
        self.assertFalse(a.dirty)
        b = a.getConfigPVs
        self.assertEqual(b[0].pvName, PV_NAME)
        self.assertEqual(b[0].readbackPvValue, PV_READBACK_VALUE)

    def test_correct_init_snapshot_with_few_pvs_one_readback(self):
        a = SARSnapshot(**{**SIMPLE_JSON_EXAMPLE_FOR_ANY_SAR_OBJECT, "snapshotItems": JSON_FOR_COMPLETE_SNAPSHOT_VALUE_FEW_PVS_ONE_WITH_READBACK})
        self.assertFalse(a.dirty)
        b = a.getConfigPVs
        self.assertEqual(b[0].pvName, PV_2_NAME)
        self.assertEqual(b[0].readbackPvValue, PV_READBACK_VALUE)
        self.assertEqual(b[1].pvName, PV_NAME)
        # self.assertEqual(b[1].readbackPvValue, PV_READBACK_VALUE)


class TestSARCompositeSnapshotsDetailed(unittest.TestCase):
    def test_correct_composite_snapshot(self):
        a = SARSnapshot(**{**SIMPLE_JSON_EXAMPLE_FOR_ANY_SAR_OBJECT, "snapshotItems": JSON_FOR_COMPLETE_SNAPSHOT_VALUE})
        b = SARSnapshot(**{**SIMPLE_JSON_EXAMPLE_FOR_ANY_SAR_OBJECT_NB2, "snapshotItems": JSON_FOR_COMPLETE_SNAPSHOT_VALUE})
        comp = SARCompositeSnapshot(uniqueId=-1, name="Some Funny Name", description="Some other description", snapshots=[a, b])
        self.assertEqual(len(comp.getSnapshots()), 2)
