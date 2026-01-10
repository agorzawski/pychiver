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
import warnings

from .sardomain import *

import json
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import os
from datetime import datetime
from abc import ABC, abstractmethod


class SaveAndRestoreEndPoint(ABC):
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

    @staticmethod
    def disable_warnings():
        warnings.warn("[pychiver:SaveRestoreService] Disabled SSL warnings!")
        warnings.filterwarnings("ignore", message="Unverified HTTPS request")
        requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

    @abstractmethod
    def getSarItem(self, uniqueId) -> SARItem:
        pass

    @abstractmethod
    def saveSarItem(self, sarItem: SARSnapshot | SARConfig, parentId=None):
        pass

    @abstractmethod
    def getChildren(self, uniqueId=None, forcedTypeTuple=None):
        pass

    @abstractmethod
    def getParent(self, uniqueId=None) -> SARItem:
        pass

    @abstractmethod
    def getCompositeSnapshotStub(self, uniqueId):
        """To be moved into @getSarItem"""
        pass

    @abstractmethod
    def getAllNodes(self, mainTree, uniqueId=None, path="", nodeType=NodeType.NONE, size=100):
        pass


class JSONSaveAndRestoreEndPoint(SaveAndRestoreEndPoint):
    """
    JMASAR EndPoint following the REST API exposed by the https://gitlab.esss.lu.se/ics-software/jmasar-service
    """

    def __init__(self, service_url=None, username=None, password=None):
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
        self.url_composite_nodes_put = "{}/composite-snapshot?parentNodeId={{}}".format(self.service_url)
        self.url_restore = "{}/restore/node?parentNodeId={{}}".format(self.service_url)
        self.url_search_referenced  = "{}/search?referenced={{}}".format(self.service_url)
        
        self._session = None
        self._username = None
        self.authenticate(username, password)

    def authenticate(self, username=None, password=None):
        self._session = requests.Session()
        if username is not None and password is not None:
            self._username = username
            self._session.auth = (username, password)
        else:
            warnings.warn("[pychiver:SaveRestoreService] No user/password authenticated. Running in the ReadOnlyMode")
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

    def _postRequest(self, url, payloadJson):
        r = self._session.post(url, files=payloadJson, verify=False)
        if r.status_code != 200:
            warnings.warn("[pychiver:SaveRestoreService] There is an issue [code {}] with the request! {}".format(r.status_code, r.content))
        return r

    def _putRequest(self, url, payloadJson, auth=None, debug=False):
        if debug:
            print("PUT: ", payloadJson)
        r = self._session.put(url, json=payloadJson, auth=auth, verify=False, headers={"Content-Type": "application/json"})
        if r.status_code != 200:
            warnings.warn("[pychiver:SaveRestoreService] There is an issue [code {}] with the request! {}".format(r.status_code, r.content))
        return r

    def status(self):
        print(self.__dict__)

    def getSarItem(self, uniqueId) -> SARItem | SARSnapshot | SARConfig | SARFolder:
        if uniqueId is None:
            raise ValueError("cannot search for None uniqueId!")
        json_data_Node = self._getRequest(self.url_node.format(uniqueId))
        return self._fromNode_toSAR(json_data_Node)

    def _fromNode_toSAR(self, json_data_Node) -> SARItem:
        uniqueId = json_data_Node["uniqueId"]
        if json_data_Node["nodeType"] == "SNAPSHOT":
            json_data = self._getRequest(self.url_snapshot.format(uniqueId))
            json_data["uniqueId"] = json_data_Node["uniqueId"]
            json_data["name"] = json_data_Node["name"]
            json_data["description"] = json_data_Node["description"]
            json_data["creator"] = json_data_Node["userName"]
            json_data["created"] = json_data_Node["created"]
            json_data["lastModified"] = json_data_Node["lastModified"]
            json_data["tags"] = json_data_Node["tags"]
            return SARSnapshot(**json_data)
        elif json_data_Node["nodeType"] == "CONFIGURATION":
            json_data = self._getRequest(self.url_config.format(uniqueId))
            json_data["uniqueId"] = json_data_Node["uniqueId"]
            json_data["name"] = json_data_Node["name"]
            json_data["description"] = json_data_Node["description"]
            return SARConfig(**json_data)
        elif json_data_Node["nodeType"] == "FOLDER":
            fullPath = self._findRootFolder(json_data_Node)
            return SARFolder(**{**json_data_Node, "fullPath": fullPath})
        elif json_data_Node["nodeType"] == "COMPOSITE_SNAPSHOT":
            return self.getCompositeSnapshot(json_data_Node["uniqueId"])
        else:
            raise ValueError("Provided data is not a valid format! Maybe something wrong with the request type?")

    def _findRootFolder(self, json_data_Node):
        deepestFolder = [json_data_Node["name"]]
        rootFolder = "Root" in json_data_Node["name"] or "root" in json_data_Node["name"]
        json_data_rep = json_data_Node
        while not rootFolder:
            json_data_rep = self._getRequest(self.url_parent.format(json_data_rep["uniqueId"]))
            rootFolder = "Root" in json_data_rep["name"] or "root" in json_data_rep["name"]
            deepestFolder.append(json_data_rep["name"])
        fullPath = "/".join(deepestFolder[::-1])
        return fullPath

    def saveSarItem(self, sarItem: SARSnapshot | SARConfig | SARFolder, parentId=None, debug=False):
        """
        following the https://github.com/ControlSystemStudio/phoebus/blob/master/services/save-and-restore/doc/index.rst
        :param debug: for service request visibility, default False
        :param sarItem: The SaveRestore Object to persist in the service
        :param parentId: The uniqueId of the parent node (folder/configuration)
        :return:
        """
        if isinstance(sarItem, SARFolder):
            folderPayload = {"userName": self._username, "name": sarItem.getName(), "description": sarItem.description, "type": sarItem.getType()}
            result = self._putRequest(url=self.url_node_put.format(parentId), payloadJson=folderPayload, debug=debug)
            if result.status_code == 200:
                sarItem.dirty = False
                sarItem.uniqueId = json.loads(result.content)["uniqueId"]
                sarItem.fullPath = self._findRootFolder(json.loads(result.content))
                warnings.warn("[pychiver:SaveRestoreService] {} saved!".format(sarItem))

        elif isinstance(sarItem, SARConfig):
            configPayload = {
                "configurationNode": {"userName": self._username, "name": sarItem.getName(), "description": sarItem.description, "type": sarItem.getType()},
                "configurationData": {
                    "pvList": [{"pvName": one.pvName, "readbackPvName": one.readbackPvName, "readOnly": one.readOnly} for one in sarItem.configList]
                },
            }
            result = self._putRequest(url=self.url_config_put.format(parentId), payloadJson=configPayload, debug=debug)
            if result.status_code == 200:
                sarItem.dirty = False
                sarItem.uniqueId = json.loads(result.content)["configurationNode"]["uniqueId"]
                warnings.warn("[pychiver:SaveRestoreService] {} saved!".format(sarItem))

        elif isinstance(sarItem, SARSnapshot):
            snapPayload = {
                "snapshotNode": {
                    "name": sarItem.getName(),
                    "description": sarItem.description,
                    "userName": self._username,
                    "nodeType": sarItem.getType(),
                },
                "snapshotData": {"snapshotItems": [o.toJson(int(datetime.now().timestamp()), 0) for o in sarItem.getConfigPVs]},
            }
            result = self._putRequest(url=self.url_snapshot_put.format(parentId), payloadJson=snapPayload, debug=debug)
            if result.status_code == 200:
                sarItem.dirty = False
                sarItem.uniqueId = json.loads(result.content)["snapshotNode"]["uniqueId"]
                warnings.warn("[pychiver:SaveRestoreService] {} saved!".format(sarItem))

        elif isinstance(sarItem, SARCompositeSnapshot):
            snapPayload = {
                "compositeSnapshotNode": {"name": sarItem.name, "nodeType": sarItem.getType(), "userName": self._username, "description": sarItem.description},
                "compositeSnapshotData": {
                    "referencedSnapshotNodes": [one for one in sarItem.getSnapshotsIds()],
                },
            }
            result = self._putRequest(url=self.url_composite_nodes_put.format(parentId), payloadJson=snapPayload, debug=debug)
            if result.status_code == 200:
                sarItem.dirty = False
                sarItem.uniqueId = json.loads(result.content)["compositeSnapshotNode"]["uniqueId"]
                warnings.warn("[pychiver:SaveRestoreService] {} saved!".format(sarItem))
        else:
            raise NotImplementedError("Saving only for SARConfig/SARSnapshot/SARFolder!")

    def getCompositeSnapshotStub(self, uniqueId):
        a = self._getRequest(self.url_composite.format(uniqueId))
        json_data_Node = self._getRequest(self.url_node.format(uniqueId))
        json_data_Node["referencedSnapshotNodes"] = a["referencedSnapshotNodes"]
        return json_data_Node

    def getReferenced(self, snapshotId):
        json = self._getRequest(self.url_search_referenced.format(snapshotId))
        toReturn = []
        for one in json["nodes"]:
            toReturn.append(self._fromNode_toSAR(one))
        return toReturn
    
    def getCompositeSnapshot(self, snapshotId, snapshotName=None):
        json = self.getCompositeSnapshotStub(snapshotId)
        snapshots = []
        for oneSnapshotId in json["referencedSnapshotNodes"]:
            a = self.getSarItem(oneSnapshotId)
            if isinstance(a, SARSnapshot):
                snapshots.append(a)
            else:
                aInception = self.getCompositeSnapshot(oneSnapshotId)
                for oneS in aInception.getSnapshots():
                    snapshots.append(oneS)
        return SARCompositeSnapshot(uniqueId=json["uniqueId"], name=json["name"], snapshots=snapshots)

    def getRoot(self):
        json_data = self._getRequest(self.service_url_root)
        return SARItem(**json_data)

    def getAllNodes(self, mainTree, uniqueId=None, path="", nodeType=NodeType.NONE, size=100):
        # TODO add ?size=value in request or equivalent,
        #  unlikely olog default size param does not alter the returned objects
        toReturn = []
        if nodeType == NodeType.NONE:
            for one in self._getRequest(self.url_snapshots):
                toReturn.append(SARItem(**one))

        elif nodeType == NodeType.COMPOSITE_SNAPSHOT:
            for one in self._getRequest(self.url_snapshots):
                if "COMPOSITE" in one["nodeType"]:
                    toReturn.append(SARItem(**one))

        elif nodeType == NodeType.SNAPSHOT:
            for one in self._getRequest(self.url_snapshots):
                if one["nodeType"] in nodeType.name:
                    toReturn.append(self.getSarItem(one["uniqueId"]))

        # TODO reenable when https://jira.ess.eu/browse/CSSTUDIO-3173 is fixed
        # elif nodeType == NodeType.CONFIGURATION:
        #     print("Getting all configurations")
        #     for one in self._getRequest(self.url_config):
        #         r = self._getRequest(self.url_parent.format(one["uniqueId"]))
        #         toReturn.append(self.getSarItem(r["uniqueId"]))
        #
        # elif nodeType == NodeType.FOLDER:
        #     for one in self._getRequest(self.url_node):
        #         r = self._getRequest(self.url_parent.format(one["uniqueId"]))
        #         toReturn.append(self.getSarItem(r["uniqueId"]))
        else:
            raise NotImplementedError("Only Definitions of Configurations, Snapshots & Composite for now. No other types supported yet!")

        for one in toReturn:
            mainTree[one.uniqueId] = one
        return toReturn

    def getChildren(self, uniqueId=None, forcedTypeTuple=None) -> list:
        if uniqueId is None:
            raise ValueError("Cannot get search for None element! Provide unique ID!")
        urlToGet = self.url_child.format(uniqueId)
        if forcedTypeTuple is None:
            #print(urlToGet)
            return [self._fromNode_toSAR(a) for a in self._getRequest(urlToGet)]  # TODO apply self._fromNode_toSAR()
        else:
            toReturn = []
            for one in self._getRequest(urlToGet):
                if one is None:
                    pass
                if one["nodeType"] == forcedTypeTuple[0]:
                    toReturn.append(forcedTypeTuple[1](**one))
            return toReturn

    def getParent(self, uniqueId=None) -> SARItem:
        if uniqueId is None:
            raise ValueError("Cannot get search for None element! Provide unique ID!")
        urlToGet = self.url_parent.format(uniqueId)
        return self._fromNode_toSAR(self._getRequest(urlToGet))

    def restore(self, snapshot: SARSnapshot):
        if isinstance(snapshot, SARSnapshot):
            r = self._postRequest(self.url_restore.format(snapshot.uniqueId), payloadJson={})
            if r.status_code == 200:
                warnings.warn("[pychiver:SaveRestoreService] {} restored!".format(snapshot))
        warnings.warn("[pychiver:SaveRestoreService] {} cannot restore non SnapshotItem!".format(snapshot))
