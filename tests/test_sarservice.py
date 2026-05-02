import unittest

from pychiver.saveandrestore import *
from pychiver.sardomain import _prep_input_for_snapshot_item

AUTHOR = "someguy"
UID_CONFIG = "U1"
UID_OF_SOME_PARENT = "U2"
UID_SNAPSHOT_1 = "U2a"
UID_SNAPSHOT_2 = "U2b"
NAME_SNAPSHOT_1 = "Snapshot1"
NAME_SNAPSHOT_1_RB = "Snapshot1 with ReadBack"
NAME_SNAPSHOT_2 = "Snapshot2"
PV1 = "PV1"
PV1_RB = "PV1_RB"
PV2 = "PV2"
PV1_LIVE_VAL = 19.9
PV1_RB_LIVE_VAL = 1999.9
PV1_MANUAL_VAL = 18.99
PV2_LIVE_VAL = 21.1
CONFIG = SARConfig(uniqueId=UID_CONFIG, name="config", sarConfigPVs=[SARConfigPV(pvName=PV1), SARConfigPV(pvName=PV2)])
CONFIG_RB = SARConfig(uniqueId=UID_CONFIG, name="config", sarConfigPVs=[SARConfigPV(pvName=PV1, readbackPvName=PV1_RB), SARConfigPV(pvName=PV2)])
SOME_CONFIG = SARConfig(uniqueId=UID_OF_SOME_PARENT, name="some config", sarConfigPVs=[])

SNAP_1_VALUES = {PV1: 20.0, PV2: 20.9}
SNAPSHOT_1 = SARSnapshot(
    uniqueId=UID_SNAPSHOT_1,
    name=NAME_SNAPSHOT_1,
    snapshotItems=[
        _prep_input_for_snapshot_item(
            o.get(),
            SNAP_1_VALUES.get(o.pvName),
            0,
        )
        for o in CONFIG.configList
    ],
)

SNAP_1_RB_VALUES = {PV1_RB: 66.0}
SNAPSHOT_1_with_RB = SARSnapshot(
    uniqueId=UID_SNAPSHOT_1,
    name=NAME_SNAPSHOT_1_RB,
    snapshotItems=[
        _prep_input_for_snapshot_item(configPv=o.get(), pvValue=SNAP_1_VALUES.get(o.pvName), unixSec=0, pvRbValue=SNAP_1_RB_VALUES.get(o.readbackPvName, None))
        for o in CONFIG_RB.configList
    ],
)

SNAP_2_VALUES = {PV1: 16.6, PV2: 20.2}
SNAPSHOT_2 = SARSnapshot(
    uniqueId=UID_SNAPSHOT_2,
    name=NAME_SNAPSHOT_2,
    snapshotItems=[
        _prep_input_for_snapshot_item(
            o.get(),
            SNAP_2_VALUES.get(o.pvName),
            0,
        )
        for o in CONFIG.configList
    ],
)


class MockUpEpics:
    pv1 = PV1_LIVE_VAL
    pv2 = PV2_LIVE_VAL
    pv1_rb = PV1_RB_LIVE_VAL

    def get(self, pvlist, timeout=1):
        if None in pvlist:
            return [None for i in pvlist]
        if PV1_RB in pvlist:
            return [self.pv1_rb, None]
        return [self.pv1, self.pv2]

    def put(self, pvlist, values, **kwargs):
        self.pv1 = values[0]
        self.pv2 = values[1]
        print(f"Restoring Local values {values}")


class MockUpEndpoint(SaveAndRestoreEndPoint):
    def getParent(self, uniqueId=None) -> SARItem:
        if uniqueId == UID_SNAPSHOT_1 or uniqueId == UID_SNAPSHOT_2:
            return CONFIG
        return SOME_CONFIG

    def getAllNodes(self, mainTree, uniqueId=None, path="", nodeType=NodeType.NONE, size=100):
        toReturn = [CONFIG, SNAPSHOT_1, SNAPSHOT_2]
        for one in toReturn:
            mainTree[one.uniqueId] = one
        return toReturn

    def __init__(self, service_url=None, username=None, password=None):
        super().__init__(service_url=service_url)

    def getSarItem(self, uniqueId) -> SARItem:
        if UID_CONFIG in uniqueId:
            return CONFIG
        if UID_SNAPSHOT_1 in uniqueId:
            return SNAPSHOT_1
        if UID_SNAPSHOT_2 in uniqueId:
            return SNAPSHOT_2

    def saveSarItem(self, sarItem: SARItem, parentId=None, debug=False):
        # for this class it just accepts as is, no issues on the service side
        if sarItem.getType() == NodeType.SNAPSHOT:
            return {
                "snapshotNode": {
                    "name": sarItem.getName(),
                    "description": sarItem.description,
                    "userName": AUTHOR,
                    "nodeType": sarItem.getType(),
                },
                "snapshotData": {"snapshotItems": [o.toJson(int(datetime.now().timestamp()), 0) for o in sarItem.getConfigPVs]},
            }
        pass

    def getChildren(self, uniqueId=None, forcedTypeTuple=None):
        return [
            {"name": NAME_SNAPSHOT_1, "uniqueId": UID_SNAPSHOT_1},
            {"name": NAME_SNAPSHOT_2, "uniqueId": UID_SNAPSHOT_2},
        ]

    def getCompositeSnapshotStub(self, uniqueId):
        pass

    def restore(self, snapshot: SARSnapshot | SARCompositeSnapshot):
        pass


class TestSARService(unittest.TestCase):
    def setUp(self):
        self.sar = SaveAndRestore(service_url="TEST", DefaultImplementation=MockUpEndpoint, Epics=MockUpEpics(), username=AUTHOR, password="testPass")

    def test_get_config(self):
        snap1 = self.sar.getSnapshot(snapshotId=UID_CONFIG)
        self.assertEqual(snap1, CONFIG)

    def test_get_snap1_byId(self):
        snap1 = self.sar.getSnapshot(snapshotId=UID_SNAPSHOT_1)
        self.assertEqual(snap1, SNAPSHOT_1)

    def test_get_snap1_byName(self):
        snap1 = self.sar.getSnapshot(snapshotName=NAME_SNAPSHOT_1)
        self.assertEqual(snap1, SNAPSHOT_1)

    def test_get_snapshots_by_configUID(self):
        snaps = self.sar.getSnapshots(configUniqueId=UID_CONFIG)
        self.assertEqual(2, len(snaps))

    def test_get_snapshots_by_config(self):
        snaps = self.sar.getSnapshots(config=CONFIG)
        self.assertEqual(2, len(snaps))

    def test_takeSnapshot(self):
        a = self.sar.takeSnapshot(CONFIG, newName="some name", newDescription="newDesc")
        self.assertEqual(PV1_LIVE_VAL, a.getStoredValue(PV1))
        self.assertEqual(PV2_LIVE_VAL, a.getStoredValue(PV2))

    def test_takeSnapshot_with_manual_PV(self):
        setValues = {PV1: PV1_MANUAL_VAL}
        a = self.sar.takeSnapshot(CONFIG, setValues=setValues, newName="some name", newDescription="newDesc")

        self.assertEqual(PV1_MANUAL_VAL, a.getStoredValue(PV1))
        self.assertEqual(PV2_LIVE_VAL, a.getStoredValue(PV2))

    def test_restoreSnapshot(self):
        self.sar.restore(SNAPSHOT_2, local=True)
        b = self.sar.takeSnapshot(CONFIG, newName="some name", newDescription="newDesc")
        self.assertEqual(SNAP_2_VALUES[PV1], b.getStoredValue(PV1))
        self.assertEqual(SNAP_2_VALUES[PV2], b.getStoredValue(PV2))

    def test_saveConfig_no_parent(self):
        with self.assertRaises(ValueError):
            self.sar.save(CONFIG)

    def test_saveConfig(self):
        self.sar.save(CONFIG, parentNodeId="SomeExistingFolder")

    def test_saveSnapshot_no_parent(self):
        self.sar.save(SNAPSHOT_1)

    def test_saveSnapshot_correct_parent(self):
        self.sar.save(SNAPSHOT_1, parentNodeId=UID_CONFIG)

    def test_saveSnapshot_incorrect_parent_corrected(self):
        self.sar.save(SNAPSHOT_1, parentNodeId="blah")

    def test_takeSnapshot_correct_with_readback(self):
        self.sar.takeSnapshot(CONFIG_RB, newName="some name", newDescription="newDesc")

    def test_saveSnapshot_correct_with_readback(self):
        self.sar.save(SNAPSHOT_1_with_RB, parentNodeId="blah")


if __name__ == "__main__":
    unittest.main()
