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
from requests.auth import HTTPBasicAuth
from requests.packages.urllib3.util.retry import Retry
import os
from datetime import datetime
from abc import ABC, abstractmethod

from .sardomain import _prep_snapshot_item


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

    @abstractmethod
    def getSarItem(self, uniqueId) -> SARItem:
        pass

    @abstractmethod
    def saveSarItem(self, sarItem: SARItem, parentId=None, author=None):
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
        # print('Asking for ', url)
        r = self._session.get(url, verify=False)
        if r.status_code == 200:
            jsonContent = json.loads(r.content)
            # print(jsonContent)
        else:
            raise ValueError("Bad Request: " + r.content)
        return jsonContent

    def _postRequest(self, url, payloadJson, auth=None):
        r = self._session.post(url, files=payloadJson, auth=auth, verify=False)
        return r

    def _putRequest(self, url, payloadJson, auth=None):
        r = self._session.put(url, json=payloadJson, auth=auth, verify=False, headers={"Content-Type": "application/json"})
        if r.status_code != 200:
            warnings.warn("[pychiver:SaveRestore ENDPOINT] There is an issue [code {}] with the request! {}".format(r.status_code, r.content))
        return r

    def status(self):
        print(self.__dict__)

    def getSarItem(self, uniqueId) -> SARItem:
        if uniqueId is None:
            raise ValueError("cannot search for None uniqueId!")
        json_data_Node = self._getRequest(self.url_node.format(uniqueId))
        return self._fromNode_toSAR(json_data_Node)

    def _fromNode_toSAR(self, json_data_Node) -> SARItem:
        uniqueId = json_data_Node["uniqueId"]
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
            json_data["tags"] = json_data_Node["tags"]
            return SARSnapshot(**json_data)
        elif json_data_Node["nodeType"] == "CONFIGURATION":
            # print('===== [ RAW CONFIGURATION data from the API] >>>')
            # print(json_data_Node)
            json_data = self._getRequest(self.url_config.format(uniqueId))
            json_data["uniqueId"] = json_data_Node["uniqueId"]
            json_data["name"] = json_data_Node["name"]
            json_data["description"] = json_data_Node["description"]
            return SARConfig(**json_data)
        elif json_data_Node["nodeType"] == "FOLDER":
            deepestFolder = [json_data_Node["name"]]
            rootFolder = "Root" in json_data_Node["name"] or "root" in json_data_Node["name"]
            json_data_rep = json_data_Node
            while not rootFolder:
                json_data_rep = self._getRequest(self.url_parent.format(json_data_rep["uniqueId"]))
                rootFolder = "Root" in json_data_rep["name"] or "root" in json_data_rep["name"]
                deepestFolder.append(json_data_rep["name"])
            fullPath = "/".join(deepestFolder[::-1])
            return SARFolder(**{**json_data_Node, "fullPath": fullPath})
        else:
            raise ValueError("Provided data is not a valid format! Maybe something wrong with the request type?")

    def saveSarItem(self, sarItem: SARSnapshot | SARConfig, parentId=None, author=None):
        """
        following the https://github.com/ControlSystemStudio/phoebus/blob/master/services/save-and-restore/doc/index.rst
        :param sarItem:
        :param parentId:
        :param author:
        :return:
        """
        # TODO might be that this one will need to be taken all the way out after new SR Roles come
        auth = HTTPBasicAuth(author, "12345678abcd")

        if isinstance(sarItem, SARConfig):
            configPayload = {
                "configurationNode": {"userName": author, "name": sarItem.getName(), "description": sarItem.description, "type": "CONFIGURATION"},
                "configurationData": {"pvList": [{"pvName": one.pvName} for one in sarItem.configList]},
                # TODO include additional stuff readback and readonly (see what format None/null True/true)
            }
            result = self._putRequest(url=self.url_config_put.format(parentId), payloadJson=configPayload, auth=auth)
            if result.status_code == 200:
                sarItem.dirty = False
                sarItem.uniqueId = json.loads(result.content)["configurationNode"]["uniqueId"]

        elif isinstance(sarItem, SARSnapshot):
            t = int(datetime.now().timestamp())
            snapPayload = {
                "snapshotNode": {
                    "name": sarItem.getName(),
                    "description": sarItem.description,
                    "userName": author,
                },
                "snapshotData": {
                    "snapshotItems": [
                        # {
                        #     "configPv": {
                        #         "pvName": o.pvName,
                        #     },
                        #     "value": {
                        #         "type": {"name": "VDouble", "version": 1}, # TODO fix that from the PV
                        #         "value": o.pvValue,
                        #         "alarm": {"severity": "NONE", "status": "NONE", "name": "NO_ALARM"},
                        #         "time": {"unixSec": t, "nanoSec": 0},
                        #         "display": {"lowDisplay": 0.0, "highDisplay": 0.0, "units": ""},
                        #         # TODO add the actual PVs info when fetchetd data -> include them in SnaphotItem
                        #     },
                        # }
                        # TODO use _prep_snapshot_item from sar domain
                        _prep_snapshot_item({"pvName": o.pvName}, o.pvValue, t,
                                            pvType=o.pvType, alarm=o.pvAlarm, display=o.pvDisplay)
                        for o in sarItem.getConfigPVs
                    ]
                },
            }
            # print("===> Just Before Upload")
            # print(snapPayload)
            result = self._putRequest(url=self.url_snapshot_put.format(parentId), payloadJson=snapPayload, auth=auth)
            if result.status_code == 200:
                sarItem.dirty = False
                sarItem.uniqueId = json.loads(result.content)["snapshotNode"]["uniqueId"]
        else:
            raise NotImplementedError("Saving only for SARConfig/SARSnapshot!")

    def getCompositeSnapshotStub(self, uniqueId):
        a = self._getRequest(self.url_composite.format(uniqueId))
        json_data_Node = self._getRequest(self.url_node.format(uniqueId))
        json_data_Node["referencedSnapshotNodes"] = a["referencedSnapshotNodes"]
        return json_data_Node

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

        elif nodeType == NodeType.VIRTUAL_SNAPSHOT:
            for one in self._getRequest(self.url_snapshots):
                if "COMPOSITE" in one["nodeType"]:
                    toReturn.append(SARItem(**one))

        elif nodeType == NodeType.SNAPSHOT:
            for one in self._getRequest(self.url_snapshots):
                if one["nodeType"] in nodeType.name:
                    toReturn.append(self.getSarItem(one["uniqueId"]))
        else:
            raise NotImplementedError("Only Definitions of Snapshots&Composite for now. No other types supported yet!")

        for one in toReturn:
            mainTree[one.uniqueId] = one
        return toReturn

    def getChildren(self, uniqueId=None, forcedTypeTuple=None) -> list:
        if uniqueId is None:
            raise ValueError("Cannot get search for None element! Provide unique ID!")
        urlToGet = self.url_child.format(uniqueId)
        if forcedTypeTuple is None:
            return self._getRequest(urlToGet)  # TODO apply self._fromNode_toSAR()
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
