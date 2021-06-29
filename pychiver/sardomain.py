"""
Domain classes for objects in Save And Restore

WIP: Some cleanup is needed as it is super bind to the JSONSaveAndRestoreEndPoint

Authors:
    A.Gorzawski <arek.gorzawski@ess.eu>
"""
import pandas
import pandas as pd


class SARItem:
    def __init__(self, **kwargs):
        if kwargs.get('name', None) is None or kwargs.get('uniqueId', None) is None:
            raise ValueError('Cannot initialise SARItem object without name or uniqueId')
        self.__dict__ = kwargs
        if kwargs.get('nodeType', None):
            self.nodeType = 'NONE'

    def getType(self) -> str:
        return self.nodeType

    def __repr__(self):
        return '{}/{}'.format(self.name, self.uniqueId)


class SARFolder(SARItem):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if kwargs.get('fullPath', None) is None:
            raise ValueError('Cannot initialise SARFolder object without path!')
        self.fullPath = kwargs.get('fullPath')

    def __repr__(self):
        return '[{} - {}]'.format(self.fullPath, self.uniqueId)


class SARConfig(SARItem):
    # TODO include the ConfigPV here
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class SARConfigPV:
    def __init__(self, **kwargs):
        self.__dict__ = kwargs
        if kwargs.get('configPv', None) is None:
            raise ValueError('Cannot initialise SARConfigPV object without pvName or readbackPvName')

    def __repr__(self):
        return '{}/{}'.format(self.pvName, self.readbackPvName)


class SARSnapshot(SARItem):
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
        base = '{}/{}\n'.format(self.name, self.uniqueId)
        if self.properties.get('golden') == 'true':
            base += ' GOLDEN \n'
        for one in self.configPVs:
            base += one.pvName + '\n'
        return base

    def getPVs(self) -> list:
        return list([o.configPv.get('pvName') for o in self.configPVs])

    def getStoredValues(self) -> pd.DataFrame:
        rowsList = []
        for one in self.configPVs:
            # print(one.__dict__)
            # print(one.value)
            # TODO solve better the JSON heritage in the object... (keys to keys to keys)
            secs_nanos = one.value.get('time').get('unixSec') + one.value.get('time').get('nanoSec') / 1e9
            rowsList.append({'PV Name': one.configPv.get('pvName'),
                             'timestamp': pd.to_datetime(secs_nanos, unit='s'),
                             'secs_nanos': secs_nanos,
                             'status_label': one.value.get('alarm').get('status'), # TODO use EpicsStatus codes.py
                             'severity_label': one.value.get('alarm').get('severity'), # TODO use EpicsSeverity codes.py
                             'stored_setpoint': one.value.get('value'),
                             })
        return pd.DataFrame(rowsList)
