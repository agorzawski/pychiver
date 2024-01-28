import unittest

from pychiver.saveandrestore import *
from pychiver.sardomain import _prep_snapshot_item

UID_CONFIG = "U1"
UID_SNAPSHOT_1 = "U2a"
UID_SNAPSHOT_2 = "U2b"

NAME_SNAPSHOT_1 = "Snapshot1"
NAME_SNAPSHOT_2 = "Snapshot2"

CONFIG = SARConfig(uniqueId=UID_CONFIG, name="config", sarConfigPVs=[SARConfigPV(pvName="PV1"), SARConfigPV(pvName="PV2")])

SNAP_1_VALUES = {"PV1": 20.0, "PV2": 10.9}
SNAPSHOT_1 = SARSnapshot(
    uniqueId=UID_SNAPSHOT_1,
    name=NAME_SNAPSHOT_1,
    snapshotItems=[
        _prep_snapshot_item(
            o.get(),
            SNAP_1_VALUES.get(o.pvName),
            0,
        )
        for o in CONFIG.configList
    ],
)

SNAP_2_VALUES = {"PV1": 16.6, "PV2": 10.2}
SNAPSHOT_2 = SARSnapshot(
    uniqueId=UID_SNAPSHOT_2,
    name=NAME_SNAPSHOT_2,
    snapshotItems=[
        _prep_snapshot_item(
            o.get(),
            SNAP_2_VALUES.get(o.pvName),
            0,
        )
        for o in CONFIG.configList
    ],
)


class MockUpEndpoint(SaveAndRestoreEndPoint):
    def getParent(self, uniqueId=None) -> SARItem:
        pass

    def getAllNodes(self, mainTree, uniqueId=None, path="", nodeType=NodeType.NONE, size=100):
        toReturn = [CONFIG, SNAPSHOT_1, SNAPSHOT_2]
        for one in toReturn:
            mainTree[one.uniqueId] = one
        return toReturn

    def __init__(self, service_url=None):
        super().__init__(service_url=service_url)

    def getSarItem(self, uniqueId) -> SARItem:
        if UID_CONFIG in uniqueId:
            return CONFIG
        if UID_SNAPSHOT_1 in uniqueId:
            return SNAPSHOT_1
        if UID_SNAPSHOT_2 in uniqueId:
            return SNAPSHOT_2

    def saveSarItem(self, sarItem: SARItem, parentId=None, author=None):
        pass

    def getChildren(self, uniqueId=None, forcedTypeTuple=None):
        return [
            {"name": NAME_SNAPSHOT_1, "uniqueId": UID_SNAPSHOT_1},
            {"name": NAME_SNAPSHOT_2, "uniqueId": UID_SNAPSHOT_2},
        ]

    def getCompositeSnapshotStub(self, uniqueId):
        pass


class TestSARItems(unittest.TestCase):
    def setUp(self):
        self.sar = SaveAndRestore(service_url="TEST", DefaultImplementation=MockUpEndpoint)

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


if __name__ == "__main__":
    unittest.main()
