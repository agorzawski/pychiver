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

import json
import warnings

import pandas
import requests
import epics
import datetime
from .sardomain import *
import pickle


class SaveAndRestoreEndPoint:

    def __init__(self, service_url=None):
        if service_url is None:
            raise ValueError('Cannot start the SAVE AND RESTORE service, please provide an url!')
        self.service_url = service_url


class JSONSaveAndRestoreEndPoint(SaveAndRestoreEndPoint):

    def __init__(self, service_url=None):
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

    def getConfigurations(self, uniqueId, mainTree, path=''):
        currentLevel = self.getChildren(uniqueId=uniqueId)
        if len(currentLevel):
            for one in currentLevel:
                if one['nodeType'] == 'SNAPSHOT':
                    pass
                currentPath = path + one['name'] + '/'
                if one['nodeType'] == 'CONFIGURATION':
                    mainTree[SARFolder(fullPath=currentPath, uniqueId=one['uniqueId'], name=one['name'])] = SARConfig(
                        **one)

                self.getConfigurations(one['uniqueId'], mainTree, path=currentPath)
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

    def getItems(self, uniqueId):
        r = requests.get(self.url_config_items.format(uniqueId))
        return r.json()


class SaveAndRestore:
    """
    Save and Restore client implementation. Exposes the

    WIP: First implementation of the abstraction for the Save And Restore interface using JMASAR JSON endpoint.
    Some parts may deserve to pushing towards the JSONSaveAndRestoreEndPoint implementation
    """

    def __init__(self, service_url=None, DefaultImplementation=JSONSaveAndRestoreEndPoint, cacheFile=None):
        """
        :param service_url:
        :param DefaultImplementation:
        """
        self.service = DefaultImplementation(service_url=service_url)
        self.epics = epics
        self.cachedConfigurations = {}
        if cacheFile is not None:
            self.cacheFile = cacheFile
            try:
                self.cachedConfigurations = pickle.load(open(cacheFile, 'rb'))
            except:
                print('No file {} found. Skipping loading from cache.'.format(self.cacheFile))

    def getSnapshots(self, config: SARConfig = None, configUniqueId: str = None) -> dict:
        print('Getting available snapshots for config ' + configUniqueId)
        # TODO add full path to the snapshot key
        # TODO add support for full configs
        # TODO add support for config names
        # configFullPath =
        aa = self.service.getChildren(uniqueId=configUniqueId)
        toReturn = {}
        for a in aa:
            bb = self.service.getItems(a['uniqueId'])
            # TODO log the data to the console
            # print(bb)
            toReturn[a['name']] = SARSnapshot(**{**a, 'snapshotIds': bb})
        return toReturn

    def getConfigurations(self, useCache=False) -> dict:
        configurations = {}
        if not useCache:
            self.service.getConfigurations(self.service.getRoot().uniqueId, configurations)
            if useCache:
                self.cacheFile = configurations
            # TODO fix the caching issues
            # pickle.dump(configurations, open(self.cacheFile, 'wb+'))
            return configurations
        else:
            print(self.cachedConfigurations)
            return configurations

    def getConfiguration(self, name=None) -> SARConfig:
        # TODO
        pass

    def compare(self, snapshot: SARSnapshot = None) -> pandas.DataFrame:
        values = epics.caget_many(pvlist=snapshot.getPVs()) #TODO chceck order PVs
        #print(values)
        df = snapshot.getStoredValues()
        df['live_values'] = values
        try:
            df['delta'] = df['stored_setpoint'] - df['live_values']
        except:
            warnings.warn("Some error occured during the delta calculation, skipping")
        return df

    def restore(self, snapshot: SARSnapshot = None):
        if not isinstance(snapshot, SARSnapshot):
            raise ValueError('For restore an SARSnapshot is required!')
        # TODO get values from snapshot
        pvsToPut = []
        valuesToPut = []
        self.epics.caput_many(pvlist=pvsToPut, values=valuesToPut)
        return 0

    def save(self, config: SARConfig = None, snapshot: SARSnapshot = None, newName=None):
        # TODO to be implemented
        pass

    def _status(self):
        self.service.status()
