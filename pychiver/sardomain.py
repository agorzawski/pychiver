"""
Domain classes for objects in Save And Restore

WIP: Some cleanup is needed as it is super bind to the JSONSaveAndRestoreEndPoint

Authors:
    A.Gorzawski <arek.gorzawski@ess.eu>
"""
import warnings

import pandas as pd
from enum import Enum, unique


@unique
class NodeType(Enum):
    NONE = " "
    FOLDER = "F"
    CONFIGURATION = "C"
    SNAPSHOT = "S"
    COMPOSITE_SNAPSHOT = "V"


class SARItem:
    """
    Top level SAR item, can be anything related to the SAR.
    """

    INIT = "stub"

    def __init__(self, **kwargs):
        self.uniqueId = self.INIT
        self.name = self.INIT
        self.description = self.INIT
        self.nodeType = NodeType.NONE
        if kwargs.get("name", None) is None or kwargs.get("uniqueId", None) is None:
            raise ValueError("Cannot initialise SARItem object without name or uniqueId")
        self.__dict__ = kwargs
        if kwargs.get("nodeType", None):
            self.nodeType = NodeType.NONE
        if kwargs.get("dirty", None) is None:
            self.dirty = False

    def getType(self) -> str:
        return self.nodeType.name

    def getName(self) -> str:
        return self.name

    def __repr__(self):
        return "[{}][{}] {} / {}".format(self.nodeType.value, "*" if self.dirty else " ", self.name, self.uniqueId)


class SARFolder(SARItem):
    """
    SAR item for the folder instance
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if kwargs.get("fullPath", None) is None:
            raise ValueError("Cannot initialise SARFolder object without path!")
        self.name = kwargs.get("name")
        self.fullPath = kwargs.get("fullPath")
        self.nodeType = NodeType.FOLDER

    def getFullPath(self) -> str:
        return self.fullPath

    def __repr__(self):
        return "[F][{} - {}]".format(self.fullPath, self.uniqueId)


class SARConfig(SARItem):
    """
    SAR item dedicated for a configuration
    """

    # FIXME duplication: configList vs pvList. pVList (native as comes to kwargs, make it unavailable) and
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
        self.nodeType = NodeType.CONFIGURATION

    def getPVs(self) -> list:
        return [o.pvName for o in self.configList]

    def getReadBackPVs(self):
        return [o.readbackPvName for o in self.configList]


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
            self.pvName = self.configPv["pvName"]
            self.pvValue = self.value["value"]
            self.type = kwargs.get("value", {}).get("type", None)
            self.alarm = kwargs.get("value", {}).get("alarm", None)
            self.display = kwargs.get("value", {}).get("display", None)
            self.enum = kwargs.get("value", {}).get("enum", None)
            if kwargs.get("readbackValue", None) is not None:
                self.readbackPvValue = kwargs.get("readbackValue", {}).get("value", None)
                self.readbackType = kwargs.get("readbackValue", {}).get("type", None)
                self.readbackAlarm = kwargs.get("readbackValue", {}).get("alarm", None)
                self.readbackDisplay = kwargs.get("readbackValue", {}).get("display", None)
                self.readbackEnum = kwargs.get("readbackValue", {}).get("enum", None)
        else:
            raise ValueError("No value given")

    def __repr__(self):
        if self.configPv["readbackPvName"] is not None:
            return "{} / {} (RB: {} / {})".format(self.pvName, self.pvValue, self.configPv["readbackPvName"], self.readbackPvValue)
        return "{} / {}".format(self.pvName, self.pvValue)

    def toJson(self, unixSec, nanoSec):
        toReturn = {
            "configPv": self.configPv,
            "value": {
                "value": self.pvValue,
                "time": {"unixSec": unixSec, "nanoSec": nanoSec},
                "type": self.type if self.type is not None else {"name": "VDouble", "version": 1},
                "alarm": self.alarm if self.alarm is not None else {"severity": "NONE", "status": "NONE", "name": "NO_ALARM"},
                "display": self.display if self.display is not None else {"lowDisplay": 0.0, "highDisplay": 0.0, "units": ""},
            },
        }

        if self.configPv.get("readbackPvName", None) is not None:
            # print(self.configPv.get("readbackPvName", None))
            toReturn["readbackValue"] = {
                "value": self.readbackPvValue,
                "time": {"unixSec": unixSec, "nanoSec": nanoSec},
                "type": self.readbackType if self.readbackType is not None else {"name": "VDouble", "version": 1},
                "alarm": self.readbackAlarm if self.readbackAlarm is not None else {"severity": "NONE", "status": "NONE", "name": "NO_ALARM"},
                "display": self.readbackDisplay if self.readbackDisplay is not None else {"lowDisplay": 0.0, "highDisplay": 0.0, "units": ""},
            }

        if self.enum is not None:
            try:
                toReturn["value"]["value"] = self.enum["labels"].index(toReturn["value"]["value"])
            except Exception:
                pass
            toReturn["value"]["enum"] = self.enum
            if self.configPv.get("readbackPvName", None) is not None:
                try:
                    toReturn["readbackValue"]["value"] = self.readbackEnum["labels"].index(toReturn["readbackValue"]["value"])
                except Exception:
                    pass
                toReturn["readbackValue"]["enum"] = self.readbackEnum

        return toReturn


class SARSnapshot(SARItem):
    """
    SAR Item dedicated for a given snapshot instance.
    """

    def __init__(self, **kwargs):
        self.creator = self.INIT
        self.created = self.INIT
        self.lastModified = self.INIT
        super().__init__(**kwargs)
        self.configPVs = []
        if kwargs.get("snapshotItems", None) is None:
            raise ValueError("Cannot initialise SARSnapshot object without snapshotItems/configPVs!")
        if kwargs.get("tags", None) is None:
            self.tags = []
        for one in kwargs.get("snapshotItems"):
            try:
                self.configPVs.append(SARSnapshotItem(**one))
            except ValueError:
                warnings.warn("Given snapshotItem {} is incomplete, " "omitting it and making your snapshot dirty".format(one))
                self.dirty = True
        self.nodeType = NodeType.SNAPSHOT

    def __repr__(self):
        base = "[S][{}] {} / {} ".format("*" if self.dirty else " ", self.name, self.uniqueId)
        for oneTag in self.tags:
            if "golden" in oneTag.get("name"):
                base += " GOLDEN"
                break
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

    def getPVs(self) -> list[str]:
        return list([o.configPv.get("pvName", []) for o in self.configPVs])

    def getReadBackPVs(self) -> list[str]:
        return list([o.configPv.get("readbackPvName", []) for o in self.configPVs])

    @property
    def getConfigPVs(self) -> list[SARSnapshotItem]:
        return self.configPVs

    def getStoredValues(self) -> pd.DataFrame:
        rowsList = []
        for one in self.configPVs:
            _append_config(rowsList, one)
        return pd.DataFrame(rowsList)

    def getStoredValue(self, pvName):
        for one in self.configPVs:
            if one.pvName == pvName:
                return one.pvValue
        raise ValueError("no {} stored in this snapshot!".format(pvName))


class SARCompositeSnapshot(SARItem):
    """
    SAR Item dedicated for a given snapshot instance.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.nodeType = NodeType.COMPOSITE_SNAPSHOT
        self.dirty = True

        if kwargs.get("properties", None) is None:
            self.properties = {"golden": "false"}

        if kwargs.get("snapshots", None) is None or len(kwargs.get("snapshots")) == 0:
            raise ValueError("Cannot initialise VirtualSnapshot object without linked snapshots!")

        self.snapshots = []
        for one in kwargs.get("snapshots"):
            if not isinstance(one, SARSnapshot):
                raise ValueError("One of the provided snapshots is not a Snapshot!")

            # TODO impose PV checks for double definitions, merging strtegy etc...
            # provide a callback
            self.snapshots.append(one)

    def __repr__(self):
        base = "[V][{}] {} / {} ".format("*" if self.dirty else " ", self.name, self.uniqueId)
        return base

    def getSnapshotsIds(self):
        return [s.uniqueId for s in self.snapshots]

    def getSnapshots(self):
        return [s for s in self.snapshots]

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

    def getStoredValue(self, pvName):
        for oneSnap in self.snapshots:
            for one in oneSnap.configPVs:
                if one.pvName == pvName:
                    return one.pvValue
        raise ValueError("no {} stored in this snapshot!".format(pvName))

    @property
    def getConfigPVs(self) -> list:
        combinedList = []
        for one in self.snapshots:
            for onePV in one.configPVs:
                combinedList.append(onePV)
        return list(combinedList)


class SarItemBuilder:
    DIRTY_SAR_ITEM = -1

    @classmethod
    def getInstance(cls):
        new_instance = cls()
        return new_instance

    def createFolder(
        self,
        name: str,
        description: str,
    ) -> SARFolder:
        return SARFolder(uniqueId=self.DIRTY_SAR_ITEM, name=name, description=description, dirty=True, fullPath=self.DIRTY_SAR_ITEM)

    def createConfiguration(self, name: str, description: str, sarConfigPVs: list[SARConfigPV]) -> SARConfig:
        """
        :param name: A unique name of the configuration
        :param description: Description of the configuration
        :param sarConfigPVs: list of SarConfigPVs to be included in the configuration
        :return:
        """
        return SARConfig(uniqueId=self.DIRTY_SAR_ITEM, sarConfigPVs=sarConfigPVs, name=name, description=description, dirty=True)

    def createCompositeSnapshot(self, name: str, description: str, snapshots: list[SARSnapshot | SARCompositeSnapshot]) -> SARCompositeSnapshot:
        """
        From the provided snapshots it creates a virtual one, that combines the source.
        Returns a non-editable bundle, that can be treated similarly like other snapshots, e.g. compare or restore.
        :param name: A unique name to add
        :param description: Description of the configuration
        :param snapshots: A list of snapshots (SARSnapshot or VirtualSnapshot) to be included in the CompositeSnapshot
        :return: a Composite Snapshot
        """
        # TODO add creation check process support
        # TODO add save to the service (ONCE THE UNDERLYING OBJECTS ARE AVAILABLE)
        return SARCompositeSnapshot(uniqueId=self.DIRTY_SAR_ITEM, name=name, description=description, snapshots=snapshots, dirty=True)


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


def _prep_input_for_snapshot_item(
    configPv,
    pvValue,
    unixSec,
    nanoSec=0,
    pvType=None,
    alarm=None,
    display=None,
    enumOptions=None,
    pvRbValue=None,
    rbNanoSec=0,
    pvRbType=None,
    alarmRb=None,
    displayRb=None,
    enumRbOptions=None,
    verb=None,
):
    toReturn = {
        "configPv": configPv,
        "value": _prep_value_block(alarm, display, nanoSec, pvType, pvValue, unixSec),
    }
    if pvRbValue is not None:
        toReturn["readbackValue"] = _prep_value_block(alarmRb, displayRb, nanoSec, pvRbType, pvRbValue, rbNanoSec)
    if enumOptions is not None:
        toReturn["value"]["enum"] = {"labels": enumOptions}
    if enumRbOptions is not None:
        toReturn["readbackValue"]["enum"] = {"labels": enumRbOptions}
    # print(toReturn)
    return toReturn


def _prep_value_block(alarm, display, nanoSec, pvType, pvValue, unixSec):
    return {
        "value": pvValue,
        "time": {"unixSec": unixSec, "nanoSec": nanoSec},
        "type": pvType if pvType is not None else {"name": "VDouble", "version": 1},
        "alarm": alarm if alarm is not None else {"severity": "NONE", "status": "NONE", "name": "NO_ALARM"},
        "display": display
        if display is not None
        else {
            "lowDisplay": 0.0,
            "highDisplay": 0.0,
            "units": "",
            "lowAlarm": 0,
            "highAlarm": 0,
            "lowWarning": 0,
            "highWarning": 0,
        },
    }
