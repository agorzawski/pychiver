"""
Domain classes for objects in Save And Restore

WIP: Some cleanup is needed as it is super bind to the JSONSaveAndRestoreEndPoint

Authors:
    A.Gorzawski <arek.gorzawski@ess.eu>
"""
import pandas as pd
from enum import Enum, unique


@unique
class NodeType(Enum):
    NONE = 0
    FOLDER = 1
    CONFIGURATION = 2
    SNAPSHOT = 3
    VIRTUAL_SNAPSHOT = 4


class SARItem:
    """
    Top level SAR item, can be anything related to the SAR.
    """

    def __init__(self, **kwargs):
        if kwargs.get("name", None) is None or kwargs.get("uniqueId", None) is None:
            raise ValueError("Cannot initialise SARItem object without name or uniqueId")
        self.__dict__ = kwargs
        if kwargs.get("nodeType", None):
            self.nodeType = NodeType.NONE

    def getType(self) -> str:
        return self.nodeType

    def getName(self) -> str:
        return self.name

    def __repr__(self):
        return "{} / {}".format(self.name, self.uniqueId)


class SARFolder(SARItem):
    """
    SAR item for the folder instance
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if kwargs.get("fullPath", None) is None:
            raise ValueError("Cannot initialise SARFolder object without path!")
        self.fullPath = kwargs.get("fullPath")

    def getFullPath(self) -> str:
        return self.fullPath

    def __repr__(self):
        return "[{} - {}]".format(self.fullPath, self.uniqueId)


class SARConfig(SARItem):
    """
    SAR item dedicated for a configuration
    """

    # TODO fix duplication: configList vs pvList. pVList (native as comes to kwargs, make it unavailable) and
    #  configList (proper Objects should be default)
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.configList = []
        if kwargs.get("pvList", None) is not None:
            for o in kwargs.get("pvList"):
                self.configList.append(SARConfigPV(**o))
        if kwargs.get("sarConfigPVs", None) is not None:
            for o in kwargs.get("sarConfigPVs"):
                if isinstance(o, SARConfigPV):
                    self.configList.append(o)
                else:
                    raise ValueError("Incorrect type of the given object ", o)

    def getPVs(self) -> list:
        return [o.pvName for o in self.configList]

    # def getJSON(self, addKeysValues=None):
    #     toDump = {"uniqueId": str(self.uniqueId),
    #                        "name": self.getName(),
    #                        "description": self.description,
    #                        "tags": None,
    #                        "properties": None,
    #                        "pvList": [o.get() for o in self.configList]}
    #     if isinstance(addKeysValues, dict):
    #         for key, value in addKeysValues.items():
    #             toDump[key] = value
    #     return json.dumps(toDump)


class SARConfigPV:
    def __init__(self, **kwargs):
        if kwargs.get("configPv", None) is None and kwargs.get("pvName", None) is None:
            raise ValueError("Cannot initialise SARConfigPV object without pvName or an entire configPV json")
        self.pvName = kwargs.get("pvName")
        self.readbackPvName = kwargs.get("readbackPvName", None)
        self.readonly = kwargs.get("readonly", False)

    def __repr__(self):
        return "{} / {} [RO:{}]".format(self.pvName, self.readbackPvName, self.readonly)

    def get(self):
        return {"pvName": self.pvName, "readbackPvName": self.readbackPvName, "readonly": self.readonly}


class SARSnapshotItem(SARConfigPV):
    # TODO fix it after fixing -SAR Config PV- (class above), expand properly for snapshotItem.
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if kwargs.get("value", None) is not None:
            self.__dict__ = kwargs
            self.pvName = self.configPv["pvName"]  # TODO somehow does not work from the super class
            self.pvValue = self.value["value"]
        else:
            raise ValueError("No value given")

    def __repr__(self):
        return "{} / {}".format(self.pvName, self.pvValue)


class SARSnapshot(SARItem):
    """
    SAR Item dedicated for a given snapshot instance.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.configPVs = []
        if kwargs.get("snapshotItems", None) is None:
            raise ValueError("Cannot initialise SARSnapshot object without configPvs!")
        if kwargs.get("properties", None) is None:
            self.properties = {"golden": "false"}
        for one in kwargs.get("snapshotItems"):
            self.configPVs.append(SARSnapshotItem(**one))

    def __repr__(self):
        base = "{} / {} ".format(self.name, self.uniqueId)
        if self.properties.get("golden") == "true":
            base += " GOLDEN"
        return base

    def metaData(self) -> dict:
        return {
            "name": self.getName(),
            "description": self.description,
            "creator": self.creator,
            "created": self.created,
            "lastModified": self.lastModified,
            "uniqueId": self.uniqueId,
            "properties": self.properties,
            "configPVs": self.configPVs,
        }

    def getPVs(self) -> list:
        return list([o.configPv.get("pvName", []) for o in self.configPVs])

    @property
    def getConfigPVs(self) -> list:
        return self.configPVs

    def getStoredValues(self) -> pd.DataFrame:
        rowsList = []
        for one in self.configPVs:
            _append_config(rowsList, one)
        return pd.DataFrame(rowsList)

    # def getJSONForService(self) -> dict:
    #     # TODO adapt for the API needs
    #     return {"uniqueId": self.uniqueId,
    #             "name": self.getName(),
    #             "description": self.description,
    #             "pvList": [self.getPVs()]}


class SARVirtualSnapshot(SARItem):
    """
    SAR Item dedicated for a given snapshot instance.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.nodeType = NodeType.VIRTUAL_SNAPSHOT

        if kwargs.get("properties", None) is None:
            self.properties = {"golden": "false"}

        if kwargs.get("snapshots", None) is None or len(kwargs.get("snapshots")) == 0:
            raise ValueError("Cannot initialise VirtualSnapshot object without linked snapshots!")

        self.snapshots = []
        for one in kwargs.get("snapshots"):
            if not isinstance(one, SARSnapshot):
                raise ValueError("One of the provided snapshots is not a Snapshot!")
                # TODO maybe just skip?

            # TODO impose PV checks for double definitions, merging strtegy etc...
            # provide a callback
            self.snapshots.append(one)

    def __repr__(self):
        base = "VIRTUAL: {} / {} ".format(self.name, self.uniqueId)
        return base

    def getSnapshots(self):
        # TODO make sure this will be not mutable (later, once ProofOfConcept done)
        return self.snapshots

    def getPVs(self) -> list:
        combinedList = []
        for one in self.snapshots:
            for onePV in one.getPVs():
                combinedList.append(onePV)
        return list(combinedList)

    def getStoredValues(self) -> pd.DataFrame:
        rowsList = []
        for oneSnap in self.snapshots:
            for one in oneSnap.configPVs:
                _append_config(rowsList, one)
        return pd.DataFrame(rowsList)

    @property
    def snapshotConfigPVs(self):
        combinedList = []
        for one in self.snapshots:
            for onePV in one.snapshotConfigPVs:
                combinedList.append(onePV)
        return list(combinedList)

    @property
    def getConfigPVs(self) -> list:
        combinedList = []
        for one in self.snapshots:
            for onePV in one.configPVs:
                combinedList.append(onePV)
        return list(combinedList)


def _append_config(rowsList, one: SARSnapshotItem):
    # TODO solve better the JSON heritage in the object... (keys to keys to keys)
    secs_nanos = one.value.get("time").get("unixSec") + one.value.get("time").get("nanoSec") / 1e9
    rowsList.append(
        {
            "pv_name": one.configPv.get("pvName"),
            "timestamp": pd.to_datetime(secs_nanos, unit="s"),
            "secs_nanos": secs_nanos,
            "status_label": one.value.get("alarm").get("status"),  # TODO use EpicsStatus codes.py
            "severity_label": one.value.get("alarm").get("severity"),  # TODO use EpicsSeverity codes.py
            "stored_value": one.value.get("value"),
        }
    )


def _prep_snapshot_item(configPv, pvValue, unixSec, nanoSec=0):
    return {
        "configPv": configPv,
        "value": {
            "value": pvValue,
            "time": {"unixSec": unixSec, "nanoSec": nanoSec},
            "alarm": {"severity": "NONE", "status": "NONE", "name": "NONE"},
        },
    }
