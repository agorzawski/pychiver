"""
Domain classes for objects in Save And Restore

WIP: Some cleanup is needed as it is super bind to the JSONSaveAndRestoreEndPoint

Authors:
    A.Gorzawski <arek.gorzawski@ess.eu>
"""
import pandas
import pandas as pd
from enum import Enum, unique


@unique
class NodeType(Enum):
    NONE = 0
    FOLDER = 1
    SAVESET = 2
    SNAPSHOT = 3
    VIRTUALSNAPSHOT = 4


class SARItem:
    """
    Top level SAR item, can be anything related to the SAR.
    """
    def __init__(self, **kwargs):
        if kwargs.get('name', None) is None or kwargs.get('uniqueId', None) is None:
            raise ValueError('Cannot initialise SARItem object without name or uniqueId')
        self.__dict__ = kwargs
        if kwargs.get('nodeType', None):
            self.nodeType = NodeType.NONE

    def getType(self) -> str:
        return self.nodeType

    def getName(self) -> str:
        return self.name

    def __repr__(self):
        return '{}/{}'.format(self.name, self.uniqueId)


class SARFolder(SARItem):
    """
    SAR item for the folder instance
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if kwargs.get('fullPath', None) is None:
            raise ValueError('Cannot initialise SARFolder object without path!')
        self.fullPath = kwargs.get('fullPath')

    def getFullPath(self) -> str:
        return self.fullPath

    def __repr__(self):
        return '[{} - {}]'.format(self.fullPath, self.uniqueId)


class SARConfig(SARItem):
    """
    SAR item dedicated for a configuration
    """
    # TODO include the ConfigPV here
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class SARConfigPV:
    def __init__(self, **kwargs):
        self.__dict__ = kwargs
        if kwargs.get('configPv', None) is None:
            raise ValueError('Cannot initialise SARConfigPV object without pvName or readbackPvName')

    # def __repr__(self):
    #     return '{}/{}'.format(self.pvName, self.readbackPvName)


class SARSnapshot(SARItem):
    """
    SAR Item dedicated for a given snapshot instance.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.configPVs = []
        if kwargs.get('snapshotIds', None) is None:
            raise ValueError('Cannot initialise SARSnapshot object without configPvs!')
        if kwargs.get('properties', None) is None:
            self.properties = {'golden': 'false'}
        for one in kwargs.get('snapshotIds'):
            self.configPVs.append(SARConfigPV(**one))

    def __repr__(self):
        base = '{}/{} '.format(self.name, self.uniqueId)
        if self.properties.get('golden') == 'true':
            base += ' GOLDEN'
        # for one in self.configPVs:
        #     base += one.pvName + '\n'
        return base

    def getPVs(self) -> list:
        return list([o.configPv.get('pvName') for o in self.configPVs])

    def getStoredValues(self) -> pd.DataFrame:
        rowsList = []
        for one in self.configPVs:
            _append_config(rowsList, one)
        return pd.DataFrame(rowsList)


class SARVirtualSnapshot(SARItem):
    """
    SAR Item dedicated for a given snapshot instance.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.nodeType = NodeType.VIRTUALSNAPSHOT

        if kwargs.get('properties', None) is None:
            self.properties = {'golden': 'false'}

        if kwargs.get('snapshots', None) is None or len(kwargs.get('snapshots')) == 0:
            raise ValueError('Cannot initialise VirtualSnapshot object without linked snapshots!')

        self.snapshots = []
        for one in kwargs.get('snapshots'):
            if not isinstance(one, SARSnapshot):
                raise ValueError('One of the provided snapshots is not a Snapshot!')
                # TODO maybe just skip?

            # TODO impose PV checks for double definitions, merging strtegy etc...
            # provide a callback
            self.snapshots.append(one)

    def __repr__(self):
        base = 'VIRTUAL: {}/{} '.format(self.name, self.uniqueId)
        return base

    def getSnapshots(self):
        return self.snapshots # TODO make sure this will be not mutable (later, once ProofOfConcept done)

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


def _append_config(rowsList, one: SARConfigPV):
    # print(one.__dict__)
    # print(one.value)
    # TODO solve better the JSON heritage in the object... (keys to keys to keys)
    secs_nanos = one.value.get('time').get('unixSec') + one.value.get('time').get('nanoSec') / 1e9
    rowsList.append({'PV Name': one.configPv.get('pvName'),
                     'timestamp': pd.to_datetime(secs_nanos, unit='s'),
                     'secs_nanos': secs_nanos,
                     'status_label': one.value.get('alarm').get('status'),  # TODO use EpicsStatus codes.py
                     'severity_label': one.value.get('alarm').get('severity'),  # TODO use EpicsSeverity codes.py
                     'stored_setpoint': one.value.get('value'),
                     })