"""
PyChiver -- A Python wrapping of ESS Archiver and Save and Restore

Copyright (c) ESS 2021

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
of the Software, and to permit persons to whom the Software is furnished to do
so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

Authors:
    A.Gorzawski <arek.gorzawski@ess.eu>
"""
import math
from json import JSONDecodeError

from .sardomain import *
from .archiver import Archiver
from .timeutils import getDateTimeObj

import requests
import epics
import os
import uuid
import pickle
import warnings
from datetime import datetime, timedelta


class SaveAndRestoreEndPoint:
    """
    An abstract class for the Save and Restore end point
    """

    def __init__(self, service_url=None):
        if service_url is None:
            raise ValueError('SaveAndRestore service URL was not provided nor set in the env. \
                                Set SAVE_AND_RESTORE_URL in your env.')
        self.service_url = service_url


class JSONSaveAndRestoreEndPoint(SaveAndRestoreEndPoint):
    """
    JMASAR EndPoint following the REST API exposed by the https://gitlab.esss.lu.se/ics-software/jmasar-service
    """

    def __init__(self, service_url=None):
        if service_url is None:
            service_url = os.getenv('SAVE_AND_RESTORE_URL', None)
        super().__init__(service_url=service_url)
        self.service_url_root = '{}/root'.format(self.service_url)
        self.url_config_snapshot = '{}/config/{{}}/snapshots'.format(self.service_url)
        self.url_config_items = '{}/snapshot/{{}}/items'.format(self.service_url)
        self.url_child = '{}/node/{{}}/children'.format(self.service_url)
        self.url_parent = '{}/node/{{}}/parent'.format(self.service_url)

    def status(self):
        print(self.__dict__)

    def getRoot(self):
        json_data = requests.get(self.service_url_root).json()
        return SARItem(**json_data)

    def getAllNodes(self, uniqueId, mainTree, path='', nodeType=NodeType.CONFIGURATION):
        currentLevel = self.getChildren(uniqueId=uniqueId)
        if len(currentLevel):
            for one in currentLevel:
                currentPath = path + one['name'] + '/'
                if one['nodeType'] == nodeType.name:
                    mainTree[SARFolder(fullPath=currentPath, uniqueId=one['uniqueId'], name=one['name'])] = SARConfig(
                        **one)

                self.getAllNodes(one['uniqueId'], mainTree, path=currentPath, nodeType=nodeType)
        else:
            pass

    def getChildren(self, uniqueId=None, forcedTypeTuple=None):
        if uniqueId is None:
            raise ValueError('Cannot get search for None element! Provide unique ID!')
        urlToGet = self.url_child.format(uniqueId)
        if forcedTypeTuple is None:
            return requests.get(urlToGet).json()
        else:
            toReturn = []
            for one in requests.get(urlToGet).json():
                if one is None:
                    pass
                if one['nodeType'] == forcedTypeTuple[0]:
                    toReturn.append(forcedTypeTuple[1](**one))
            return toReturn

    def getParent(self, uniqueId=None):
        if uniqueId is None:
            raise ValueError('Cannot get search for None element! Provide unique ID!')
        urlToGet = self.url_parent.format(uniqueId)
        return requests.get(urlToGet).json()

    def getItems(self, uniqueId):
        r = requests.get(self.url_config_items.format(uniqueId))
        return r.json()


class SaveAndRestore:
    """
    Save and Restore client implementation. Exposes the main functionality.
    Allows to get configurations and snapshots for a given configuration.

    All snapshots have DataFrame representation

    WIP: First implementation of the abstraction for the Save And Restore interface using JMASAR JSON endpoint.
    Some parts may deserve to pushing towards the JSONSaveAndRestoreEndPoint implementation
    """

    def __init__(self, service_url: str, DefaultImplementation=JSONSaveAndRestoreEndPoint, cacheFile=None,
                 archiver_url: str = None):
        """
        Initialises the client class for Save and Restore taking one obligatory argument that is the service URL.

        If cache file set to True, client will use the configurations setup stored in the local file.
        If local file will not be found, the first time user will call getConfigurations() a local file will be created.

        :param service_url: required, an url for the service
        :param archiver_url: optional, url for Archiver service, for comparisons
        :param DefaultImplementation: optional, default is JSONSaveAndRestoreEndPoint
        :param cacheFile: optional, default is False
        """
        warnings.warn('This is a prototype, use with caution!')
        self.service = DefaultImplementation(service_url=service_url)
        self.epics = epics
        self.cachedConfigurations = {}
        self.cacheFile = None
        if cacheFile is not None:
            self.cacheFile = cacheFile
            try:
                self.cachedConfigurations = pickle.load(open(cacheFile, 'rb'))
            except:
                print('No file {} found. Skipping loading from cache.'.format(self.cacheFile))
        self._archiver = None
        if archiver_url is not None:
            self._archiver = Archiver(archiver_url=archiver_url)

    def takeSnapshot(self, config: SARConfig = None) -> SARSnapshot:
        """
        Prepares a snapshot for a given config.
        :param config:
        :return: a mutable snapshot object to be complemented with missing information and saved
        """
        raise NotImplementedError("Taking snapshots is not implement yet!")

    def getSnapshot(self, snapshotId: str = None, snapshotName: str = None) -> SARSnapshot:
        """
        Returns one snapshot by provided unique ID
        :param snapshotName: individual snapshot name
        :param snapshotId: individual snapshot ID
        :return: snapshot
        :raises ValueError if no snapshot found for the given snapshotId or snapshotName
        """
        if snapshotName is not None and snapshotId is not None:
            raise NotImplementedError("Cannot use both criterias (snaphotId or snapshotName)")
        if snapshotId is not None:
            try:
                parentInfo = self.service.getParent(uniqueId=snapshotId)
                allInParentConfig = self.service.getChildren(uniqueId=parentInfo['uniqueId'])
                for one in allInParentConfig:
                    if one['uniqueId'] == snapshotId:
                        return SARSnapshot(**{**one, 'snapshotConfigPVs': self.service.getItems(one['uniqueId'])})
            except JSONDecodeError:
                warnings.warn('Something went wrong with finding the provided snapshotId=\'{}\''.format(snapshotId))
        if snapshotName is not None:
            allSnapshots = self.getAll(nodeType=NodeType.SNAPSHOT)
            # TODO add finding the last one
            for one in allSnapshots.values():
                if snapshotName in one.name:
                    return self.getSnapshot(snapshotId=one.uniqueId)
        raise ValueError('Cannot find the snapshot for a provided snapshotId or snapshotName')

    def getSnapshots(self, config: SARConfig = None, configUniqueId: str = None) -> dict:
        """
        Returns all snapshots for a given config. Either config (SARConfig) or configUniqueId (str) needs to be provided

        :param config:
        :param configUniqueId:
        :return: a dict of SnapshotsName -> SARSnapshot
        """
        print('Getting available snapshots for config ' + configUniqueId)
        # TODO add full path to the snapshot key
        # TODO add support for full configs
        # TODO add support for config names
        # configFullPath =
        allInParentConfig = self.service.getChildren(uniqueId=configUniqueId)
        toReturn = {}
        for one in allInParentConfig:
            bb = self.service.getItems(one['uniqueId'])
            # TODO log the data to the console
            toReturn[one['name']] = SARSnapshot(**{**one, 'snapshotConfigPVs': bb})
        return toReturn

    def createVirtualSnapshot(self, name, snapshots) -> SARVirtualSnapshot:
        """
        From the provided snapshots it creates a virtual one, that combines the source.
        Returns a non editable bundle, that can be treated similarly like other snapshots, e.g. compare or restore.
        :param name: An unique name to add
        :param snapshots: a list of snapshots (SARSnapshot)
        :return: a virtual snapshot
        """
        # TODO add creation check process support
        # TODO add save to the service (ONCE THE UNDERLYING OBJECTS ARE AVAILABLE)
        return SARVirtualSnapshot(uniqueId=uuid.uuid4(), name=name,
                                  snapshots=snapshots)

    def getAll(self, useCache=False, nodeType=NodeType.CONFIGURATION) -> dict:
        """
        Returns all configurations found in the system. If useCache is True, it retrieves it from the local file.

        :param useCache: optional, default False
        :return:
        """
        configurations = {}
        if not useCache:
            self.service.getAllNodes(self.service.getRoot().uniqueId, configurations, nodeType=nodeType)
            self._updateCache(configurations)
            return configurations
        else:
            print(self.cachedConfigurations)
            return self.cachedConfigurations

    def getConfiguration(self, name=None) -> SARConfig:
        # TODO provide an easy way to search through the configurations (ie. without pulling all conf every time)
        # this has also a TODO on the https://gitlab.esss.lu.se/ics-software/jmasar-service
        raise NotImplementedError('Not implemented yet!')

    def compareAndCheck(self, snapshot: SARSnapshot = None, date_time=None, verbose=False,
                        timeout=1) -> bool:
        """
        Provides the true/false result of the comparison for a given snapshot.
        True, when all the live/archived values match the ones that are saved.
        False, when one (or more) saved values does not match the read values

        :param timeout:
        :param verbose:
        :param date_time:
        :param snapshot: existing snapshot,
        :date_time: default None
        :return: True/False
        """
        comparisonResult = self.compare(snapshot=snapshot, date_time=date_time, verbose=verbose, timeout=timeout)
        comparisonResult = comparisonResult[~comparisonResult['delta'].between(0, 0)]
        return len(comparisonResult) == 0

    def compare(self, snapshot: SARSnapshot = None, date_time=None, verbose=False, timeout=1) -> pandas.DataFrame:
        """
        Provides the way of comparing a snapshot to the:
         - live values, that are retrieved by pyepics.
         - archived values in the archiver at given date_time

        :param timeout:
        :param verbose:
        :param date_time:
        :param snapshot: existing snapshot,
        :date_time: default None
        :return: DataFrame for given snapshot, enlarged with live_values and archived_values and their deltas to the setpoitns
        """
        df = snapshot.getStoredValues()
        if date_time is None:
            # TODO add some comperror support
            values = self.epics.caget_many(pvlist=snapshot.getPVs(), timeout=timeout)  # TODO check order PVs
            df['live_values'] = values
            df['archived_values'] = math.nan
            try:
                df['delta'] = df['stored_value'] - df['live_values']
            except:
                warnings.warn("Some error occurred during the delta calculation, skipping")

        if isinstance(date_time, datetime) or isinstance(date_time, str):
            if self._archiver is None:
                raise ValueError('Service not instantiated with the archiver link. Cannot perform that action!')
            date_time_to_consider = getDateTimeObj(date_time)
            print(date_time_to_consider)
            startD = date_time_to_consider - timedelta(seconds=1)  # TODO archiver window to consider?
            endD = date_time_to_consider + timedelta(seconds=1)
            data = self._archiver.get(snapshot.getPVs(), start_date=startD, end_date=endD, verbose=verbose)
            print("=======")
            print(data)
            print("=======")
            df['live_values'] = math.nan
            df['archived_values'] = math.nan
            # TODO finish this comparison with a proper data extracted
            raise NotImplementedError("Not implemented until the end!")
        return df

    def restore(self, snapshot: SARSnapshot = None, **kwargs):
        """
        Sets the PVs to their values as provided in the snapshot

        :param snapshot:
        :return:
        """
        if not isinstance(snapshot, SARSnapshot):
            raise ValueError('For restore an SARSnapshot is required!')
        try:
            pvsToPut = [one['configPv']['pvName'] for one in snapshot.snapshotConfigPVs ]
            valuesToPut = [one['value']['value'] for one in snapshot.snapshotConfigPVs ]
            self.epics.caput_many(pvlist=pvsToPut, values=valuesToPut, **kwargs)
        except Exception:
            warnings.warn('Something went wrong. Values not set.')
        return 0

    def save(self, config: SARConfig = None, snapshot: SARSnapshot = None, newName=None):
        # TODO to be implemented, to be found in the REST Api how to do it
        raise NotImplementedError('Not implemented yet!')

    def _updateCache(self, newConfiguration):
        import copy
        self.cachedConfigurations = copy.deepcopy(newConfiguration)
        if self.cacheFile is not None:
            pickle.dump(self.cachedConfigurations, open(self.cacheFile, 'wb+'))

    def _status(self):
        self.service.status()
