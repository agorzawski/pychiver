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
import pandas
import math
from json import JSONDecodeError

from .sardomain import *
from .archiver import Archiver
from .timeutils import getDateTimeObj

import requests
from requests.adapters import HTTPAdapter
from requests.auth import HTTPBasicAuth
from requests.packages.urllib3.util.retry import Retry
import epics
import os
import uuid
import pickle
import warnings
from datetime import datetime, timedelta
from .instances import DEFAULT_SAVE_RESTORE


class SaveAndRestoreEndPoint:
    """
    An abstract class for the Save and Restore end point
    """

    def __init__(self, service_url=None):
        if service_url is None:
            raise ValueError(
                "SaveAndRestore service URL was not provided nor set in the env. \
                                Set SAVE_AND_RESTORE_URL in your env."
            )
        self.service_url = service_url


class JSONSaveAndRestoreEndPoint(SaveAndRestoreEndPoint):
    """
    JMASAR EndPoint following the REST API exposed by the https://gitlab.esss.lu.se/ics-software/jmasar-service
    """

    def __init__(self, service_url=None):
        if service_url is None:
            service_url = os.getenv("SAVE_AND_RESTORE_URL", None)
        super().__init__(service_url=service_url)
        self.service_url_root = "{}/root".format(self.service_url)  # deprecated

        self.url_node = "{}/node/{{}}".format(self.service_url)
        self.url_node_put = "{}/node?parentNodeId={{}}".format(self.service_url)
        self.url_child = "{}/node/{{}}/children".format(self.service_url)
        self.url_parent = "{}/node/{{}}/parent".format(self.service_url)
        self.url_snapshot = "{}/snapshot/{{}}".format(self.service_url)
        self.url_snapshot_put = "{}/snapshot?parentNodeId={{}}".format(self.service_url)
        self.url_config = "{}/config/{{}}".format(self.service_url)
        self.url_config_put = "{}/config?parentNodeId={{}}".format(self.service_url)
        self.url_snapshots = "{}/snapshots".format(self.service_url)
        self.url_composite = "{}/composite-snapshot/{{}}".format(self.service_url)
        self.url_composite_nodes = "{}/composite-snapshot/{{}}/nodes".format(self.service_url)

        self._session = requests.Session()
        retry = Retry(connect=5, backoff_factor=0.5)
        adapter = HTTPAdapter(max_retries=retry)
        self._session.mount("https://", adapter)

    def _getRequest(self, url):
        r = self._session.get(url, verify=False)
        if r.status_code == 200:
            jsonContent = json.loads(r.content)
        else:
            raise ValueError("Bad Request: " + r.content)
        return jsonContent

    def _postRequest(self, url, payloadJson, auth=None):
        r = self._session.post(url, files=payloadJson, auth=auth, verify=False)
        return r

    def _putRequest(self, url, payloadJson, auth=None):
        r = self._session.put(url, json=payloadJson, auth=auth, verify=False, headers={"Content-Type": "application/json"})
        return r

    def status(self):
        print(self.__dict__)

    def getSnapshot(self, uniqueId):
        # TODO rename that function for more generic name (getNodeDetails?)
        json_data_Node = self._getRequest(self.url_node.format(uniqueId))
        if json_data_Node["nodeType"] == "SNAPSHOT":
            json_data = self._getRequest(self.url_snapshot.format(uniqueId))
            # print('===== [ RAW SNAPSHOT data from the API] >>>')
            # print(json_data_Node)
            json_data["uniqueId"] = json_data_Node["uniqueId"]
            json_data["name"] = json_data_Node["name"]
            json_data["description"] = json_data_Node["description"]
            json_data["creator"] = json_data_Node["userName"]
            json_data["created"] = json_data_Node["created"]
            json_data["lastModified"] = json_data_Node["lastModified"]
            return SARSnapshot(**json_data)
        elif json_data_Node["nodeType"] == "CONFIGURATION":
            # print('===== [ RAW CONFIGURATION data from the API] >>>')
            # print(json_data_Node)
            json_data = self._getRequest(self.url_config.format(uniqueId))
            json_data["uniqueId"] = json_data_Node["uniqueId"]
            json_data["name"] = json_data_Node["name"]
            json_data["description"] = json_data_Node["description"]
            return SARConfig(**json_data)
        else:
            return None

    def save(self, sarItem: SARItem, parentId=None, author=None):
        # WIP following the https://github.com/ControlSystemStudio/phoebus/blob/master/services/save-and-restore/doc/index.rst

        # TODO check if item can be saved for parent
        # TODO check if item is not duplicate? (lists_pvs/ values)
        auth = HTTPBasicAuth(author, "12345678abcd")

        if isinstance(sarItem, SARConfig):
            # print(self.url_config_put.format(parentId))
            configPayload = {
                "configurationNode": {"userName": author, "name": sarItem.getName(), "description": sarItem.description, "type": "CONFIGURATION"},
                "configurationData": {"pvList": [{"pvName": one.pvName} for one in sarItem.configList]},
                # TODO include additional stuff
            }
            # print(configPayload)
            result = self._putRequest(url=self.url_config_put.format(parentId), payloadJson=configPayload, auth=auth)
            sarItem.uniqueId = json.loads(result.content)["configurationNode"]["uniqueId"]

        elif isinstance(sarItem, SARSnapshot):
            # print(self.url_snapshot_put.format(parentId))
            t = int(datetime.now().timestamp())
            snapPayload = {
                "snapshotNode": {
                    "name": sarItem.getName(),
                    "description": sarItem.description,
                    "userName": author,
                },
                "snapshotData": {
                    "snapshotItems": [
                        {
                            "configPv": {
                                "pvName": o.pvName,
                            },
                            "value": {
                                "type": {"name": "VDouble", "version": 1},
                                "value": o.pvValue,
                                "alarm": {"severity": "NONE", "status": "NONE", "name": "NO_ALARM"},
                                "time": {"unixSec": t, "nanoSec": 0},
                                "display": {"lowDisplay": 0.0, "highDisplay": 0.0, "units": ""},
                            },
                        }
                        for o in sarItem.getConfigPVs
                    ]
                },
            }
            # print("===> Just Before Upload")
            # print(snapPayload)
            result = self._putRequest(url=self.url_snapshot_put.format(parentId), payloadJson=snapPayload, auth=auth)
            # TODO update uniqueID
            print(result)

        else:
            raise NotImplementedError("Not implemented yet!")

    def getCompositeSnapshotStub(self, uniqueId):
        a = self._getRequest(self.url_composite.format(uniqueId))
        json_data_Node = self._getRequest(self.url_node.format(uniqueId))
        json_data_Node["referencedSnapshotNodes"] = a["referencedSnapshotNodes"]
        return json_data_Node

    def getRoot(self):
        json_data = self._getRequest(self.service_url_root)
        return SARItem(**json_data)

    def getAllNodes(self, mainTree, uniqueId=None, path="", nodeType=NodeType.NONE, size=100):
        # TODO add ?size=value in request or equivalent, unlikely olog default size param does not alter the returned objects
        toReturn = []
        if nodeType == NodeType.NONE:
            for one in self._getRequest(self.url_snapshots):
                toReturn.append(SARItem(**one))

        elif nodeType == NodeType.VIRTUAL_SNAPSHOT:
            for one in self._getRequest(self.url_snapshots):
                if "COMPOSITE" in one["nodeType"]:
                    toReturn.append(SARItem(**one))

        elif nodeType == NodeType.SNAPSHOT:
            for one in self._getRequest(self.url_snapshots):
                toReturn.append(self.getSnapshot(one["uniqueId"]))
        else:
            raise NotImplementedError("Only Definitions of Snapshots&Composite, and Snapshots for now. No other types supported yet!")

        for one in toReturn:
            mainTree[one.uniqueId] = one
        return toReturn

    def getChildren(self, uniqueId=None, forcedTypeTuple=None):
        if uniqueId is None:
            raise ValueError("Cannot get search for None element! Provide unique ID!")
        urlToGet = self.url_child.format(uniqueId)
        if forcedTypeTuple is None:
            return self._getRequest(urlToGet)
        else:
            toReturn = []
            for one in self._getRequest(urlToGet):
                if one is None:
                    pass
                if one["nodeType"] == forcedTypeTuple[0]:
                    toReturn.append(forcedTypeTuple[1](**one))
            return toReturn

    def getParent(self, uniqueId=None):
        if uniqueId is None:
            raise ValueError("Cannot get search for None element! Provide unique ID!")
        urlToGet = self.url_parent.format(uniqueId)
        return self._getRequest(urlToGet)


class SaveAndRestore:
    """
    Save and Restore client implementation. Exposes the main functionality.
    Allows to get configurations and snapshots for a given configuration.

    All snapshots have DataFrame representation

    WIP: First implementation of the abstraction for the Save And Restore interface using JMASAR JSON endpoint.
    Some parts may deserve to pushing towards the JSONSaveAndRestoreEndPoint implementation
    """

    def __init__(self, service_url: str = DEFAULT_SAVE_RESTORE, DefaultImplementation=JSONSaveAndRestoreEndPoint, cacheFile=None, archiver_url: str = None):
        """
        Initialises the client class for Save and Restore taking one obligatory argument that is the service URL.

        If cache file set to True, client will use the configurations setup stored in the local file.
        If local file will not be found, the first time user will call getConfigurations() a local file will be created.

        :param service_url: required, an url for the service
        :param archiver_url: optional, url for Archiver service, for comparisons
        :param DefaultImplementation: optional, default is JSONSaveAndRestoreEndPoint
        :param cacheFile: optional, default is False
        """
        warnings.warn("This is a prototype, use with caution!")
        self.service = DefaultImplementation(service_url=service_url)
        self.epics = epics
        self.cachedConfigurations = {}
        self.cacheFile = None
        if cacheFile is not None:
            self.cacheFile = cacheFile
            try:
                self.cachedConfigurations = pickle.load(open(cacheFile, "rb"))
            except:
                print("No file {} found. Skipping loading from cache.".format(self.cacheFile))
        self._archiver = None
        if archiver_url is not None:
            self._archiver = Archiver(archiver_url=archiver_url)

    def takeSnapshot(self, base: SARConfig | SARSnapshot = None, timeout=1, setValues=None, newName=None, newDescription=None) -> SARSnapshot:
        """
        Takes a snapshot for a given config or retakes for existing snapshot
        :param setValues:
        :param base: can be SARConfig or a SARSnapshot,
        :param newDescription: description of the snapshot to take,
        :param newName: name of the snapshot to take,
        :param timeout: default 1,
        :return: a mutable snapshot object to be complemented with missing information and saved,
        """
        liveValues = self.epics.caget_many(pvlist=base.getPVs(), timeout=timeout)
        newLiveValues = [{k: v} for k, v in zip(base.getPVs(), liveValues)]
        if isinstance(base, SARConfig):
            if setValues is None:
                setValues = newLiveValues[0]
            snap = {
                "uniqueId": -1,
                "name": newName,
                "description": newDescription,
                "snapshotItems": [
                    {
                        "configPv": o.get(),
                        "value": {
                            "value": setValues.get(o.pvName),
                            "time": {"unixSec": int(datetime.now().timestamp()), "nanoSec": 0},
                            "alarm": {"severity": "NONE", "status": "NONE", "name": "NONE"},
                        },
                    }
                    for o in base.configList
                ],
            }
            return SARSnapshot(**snap)
        else:
            raise NotImplementedError("Taking snapshots is not implement yet!")

    def saveSnapshot(
        self,
        snapshot: SARSnapshot = None,
        authToken=None,
    ):
        raise NotImplementedError("Taking snapshots is not implement yet!")

    def createConfiguration(self, name: str = None, sarConfigPVs: list = None, authToken=None, description=None) -> SARConfig:
        """
        :param description:
        :param name:
        :param sarConfigPVs:
        :param authToken:
        :return:
        """

        return SARConfig(uniqueId=uuid.uuid4(), sarConfigPVs=sarConfigPVs, name=name, description=description)

    def getSnapshot(self, snapshotId: str = None, snapshotName: str = None, sarItem: SARItem = None) -> SARSnapshot:
        """
        Returns one snapshot by provided unique ID
        :param snapshotName: individual snapshot name
        :param snapshotId: individual snapshot ID
        :return: snapshot
        :raises ValueError if no snapshot found for the given snapshotId or snapshotName
        """
        if snapshotName is not None and snapshotId is not None and sarItem is not None:
            raise NotImplementedError("Cannot use both criteria (snapshotId or snapshotName)")
        if sarItem is not None:
            return self.service.getSnapshot(sarItem.uniqueId)
        if snapshotId is not None:
            try:
                return self.service.getSnapshot(snapshotId)
            except JSONDecodeError:
                warnings.warn("Something went wrong with finding the provided snapshotId='{}'".format(snapshotId))
        if snapshotName is not None:
            allSnapshots = self.getAll()
            # TODO add finding the last one
            for one in allSnapshots.values():
                if snapshotName in one.name:
                    return self.getSnapshot(snapshotId=one.uniqueId)
        raise ValueError("Cannot find the snapshot for a provided snapshotId or snapshotName")

    def getSnapshots(self, config: SARConfig = None, configUniqueId: str = None) -> dict:
        """
        Returns all snapshots for a given config. Either config (SARConfig) or configUniqueId (str) needs to be provided

        :param config:
        :param configUniqueId:
        :return: a dict of SnapshotsName -> SARSnapshot
        """
        print("Getting available snapshots for config " + configUniqueId)
        # TODO add support for config names

        if config is not None and configUniqueId is not None:
            raise ValueError("You need to providfe SARConfig or congfigUniqueId")

        if not isinstance(config, SARConfig) and configUniqueId is None:
            raise ValueError("Cannot find snapshots for not SARConfig")

        uniqueId = configUniqueId if configUniqueId is not None else config.uniqueId
        allInParentConfig = self.service.getChildren(uniqueId=uniqueId)
        toReturn = {}
        for one in allInParentConfig:
            toReturn[one["name"]] = self.service.getSnapshot(one["uniqueId"])
        return toReturn

    def getCompositeSnapshot(self, snapshotId: str = None, snapshotName: str = None) -> SARVirtualSnapshot:
        """
        :return: a virtual snapshot
        """
        json = self.service.getCompositeSnapshotStub(snapshotId)
        snapshots = []
        for oneSnapshotId in json["referencedSnapshotNodes"]:
            a = self.service.getSnapshot(oneSnapshotId)
            if isinstance(a, SARSnapshot):
                snapshots.append(a)
            else:
                aInception = self.getCompositeSnapshot(oneSnapshotId)
                for oneS in aInception.getSnapshots():
                    snapshots.append(oneS)
        return SARVirtualSnapshot(uniqueId=json["uniqueId"], name=json["name"], snapshots=snapshots)

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
        return SARVirtualSnapshot(uniqueId=uuid.uuid4(), name=name, snapshots=snapshots)

    def getAll(self, useCache=False, nodeType=NodeType.NONE) -> dict:
        """
        Returns all configurations found in the system. If useCache is True, it retrieves it from the local file.

        :param useCache: optional, default False
        :return:
        """
        configurations = {}
        if not useCache:
            self.service.getAllNodes(configurations, nodeType=nodeType)
            self._updateCache(configurations)
            return configurations
        else:
            print(self.cachedConfigurations)
            return self.cachedConfigurations

    def getConfiguration(self, configId: str = None, name: str = None) -> SARConfig:
        # TODO provide an easy way to search through the configurations (ie. without pulling all conf every time)
        # this has also a TODO on the https://gitlab.esss.lu.se/ics-software/jmasar-service

        if configId is not None:
            return self.service.getSnapshot(configId)
        else:
            raise NotImplementedError("Not implemented yet!")

    def compareAndCheck(self, snapshot: SARSnapshot = None, date_time=None, timeout=1) -> bool:
        """
        Provides the true/false result of the comparison for a given snapshot.
        True, when all the live/archived values match the ones that are saved.
        False, when one (or more) saved values does not match the read values

        :param timeout:
        :param date_time:
        :param snapshot: existing snapshot,
        :date_time: default None
        :return: True/False
        """
        comparisonResult = self.compare(snapshot=snapshot, date_time=date_time, timeout=timeout)
        comparisonResult = comparisonResult[~comparisonResult["delta"].between(0, 0)]
        return len(comparisonResult) == 0

    def compare(self, snapshot: SARSnapshot = None, date_time=None, timeout=1) -> pandas.DataFrame:
        """
        Provides the way of comparing a snapshot to the:
         - live values, that are retrieved by pyepics.
         - archived values in the archiver at given date_time

        :param timeout:
        :param date_time:
        :param snapshot: existing snapshot,
        :date_time: default None
        :return: DataFrame for given snapshot, enlarged with live_values and archived_values and their deltas to the setpoitns
        """
        df = snapshot.getStoredValues()
        if date_time is None:
            # TODO add some comperror support
            values = self.epics.caget_many(pvlist=snapshot.getPVs(), timeout=timeout)  # TODO check order PVs
            df["live_value"] = values
            df["archived_value"] = math.nan
            try:
                df["delta"] = df["stored_value"] - df["live_value"]
            except:
                warnings.warn("Some error occurred during the delta calculation, skipping")

        if isinstance(date_time, datetime) or isinstance(date_time, str):
            if self._archiver is None:
                raise ValueError("Service not instantiated with the archiver link. Cannot perform that action!")
            date_time_to_consider = getDateTimeObj(date_time)
            print(date_time_to_consider)
            startD = date_time_to_consider - timedelta(seconds=1)  # TODO archiver window to consider?
            endD = date_time_to_consider + timedelta(seconds=1)
            data = self._archiver.get(snapshot.getPVs(), start_date=startD, end_date=endD)
            print("=======")
            print(data)
            print("=======")
            df["live_value"] = math.nan
            values = []
            for one in snapshot.getPVs():
                val = math.nan
                if len(data[one].index) > 1:
                    val = data[one]["val"][0]  # FIXME better access to the value stored
                values.append(val)
            df["archived_value"] = values
        return df

    def restore(self, snapshot: SARSnapshot = None, **kwargs):
        """
        Sets the PVs to their values as provided in the snapshot

        :param snapshot:
        :return:
        """
        if not isinstance(snapshot, SARSnapshot):
            raise ValueError("For restore an SARSnapshot is required!")
        try:
            pvsToPut = [one.configPv["pvName"] for one in snapshot.getConfigPVs]
            valuesToPut = [one.value["value"] for one in snapshot.getConfigPVs]
            self.epics.caput_many(pvlist=pvsToPut, values=valuesToPut, **kwargs)
        except Exception:
            warnings.warn("Something went wrong. Values not set.")
        return 0

    def save(self, sarItem: SARConfig | SARSnapshot = None, parentNode: SARFolder = None):
        # TODO to be implemented, to be found in the REST Api how to do it
        raise NotImplementedError("Not implemented yet!")

    def _updateCache(self, newConfiguration):
        import copy

        self.cachedConfigurations = copy.deepcopy(newConfiguration)
        if self.cacheFile is not None:
            pickle.dump(self.cachedConfigurations, open(self.cacheFile, "wb+"))

    def _status(self):
        self.service.status()
