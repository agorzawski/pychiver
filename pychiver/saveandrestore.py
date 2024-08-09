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
from numpy import ndarray
import pandas
import math
from json import JSONDecodeError
from .endpoints_sar import *
from .sardomain import _prep_input_for_snapshot_item
from .archiver import Archiver
from .timeutils import getDateTimeObj, datetime, timedelta
from .instances import DEFAULT_SAVE_RESTORE
from p4p.client.thread import Context
from p4p.nt.scalar import ntwrappercommon, ntnumericarray, ntfloat
from p4p.nt.enum import ntenum

import pickle
import warnings


class SaveAndRestore:
    """
    Save and Restore client implementation. Exposes the main functionality.
    Allows to get configurations and snapshots for a given configuration.

    All snapshots have DataFrame representation

    WIP: First implementation of the abstraction for the Save And Restore interface using JMASAR JSON endpoint.
    Some parts may deserve to pushing towards the JSONSaveAndRestoreEndPoint implementation
    """

    def __init__(
        self,
        service_url: str = DEFAULT_SAVE_RESTORE,
        DefaultImplementation=JSONSaveAndRestoreEndPoint,
        username=None,
        password=None,
        Epics=Context("pva"),
        cacheFile=None,
        archiver_url: str = None,
    ):
        """
        Initialises the client class for Save and Restore taking one obligatory argument that is the service URL.

        If cache file set to True, client will use the configurations setup stored in the local file.
        If local file will not be found, the first time user will call getConfigurations() a local file will be created.

        :param service_url: required, an url for the service
        :param username: username for performing editing actions (i.e. creates). None, for read only.
        :param password: relevant password, None for read only
        :param Epics: relevant epics (p4p) context, default pva,
        :param archiver_url: optional, url for Archiver service, for comparisons
        :param DefaultImplementation: optional, default is JSONSaveAndRestoreEndPoint
        :param cacheFile: optional, default is False
        """
        warnings.warn("[pychiver:SaveRestore] This is a prototype, use with caution!")
        self._username = username
        self.service = DefaultImplementation(service_url=service_url, username=username, password=password)
        self.epics = Epics
        self.cachedConfigurations = {}
        self.cacheFile = None
        if cacheFile is not None:
            self.cacheFile = cacheFile
            try:
                self.cachedConfigurations = pickle.load(open(cacheFile, "rb"))
            except:
                warnings.warn("[pychiver:SaveRestore] No file {} found. " "Skipping loading from cache.".format(self.cacheFile))
        self._archiver = None
        if archiver_url is not None:
            self._archiver = Archiver(archiver_url=archiver_url)

    def authenticate(self, username=None, password=None):
        if username is not None and password is not None:
            self._username = username
            self.service.authenticate(username=username, password=password)

    def takeSnapshot(
        self,
        base: SARConfig | SARSnapshot,
        setValues=None,
        newName=None,
        newDescription=None,
    ) -> SARSnapshot:
        """
        Takes a snapshot for a given config or retakes for the existing snapshot.
        Can be updated with the additionally provided Pv->Value as setValues
        :param setValues: optional, default None (i.e. live values from EPICS will be fetched), should be provided in
        a form of a dict of {PVName -> value}.
        :param base: can be SARConfig or a SARSnapshot,
        :param newDescription: description of the snapshot to take,
        :param newName: name of the snapshot to take,
        :return: a mutable snapshot object to be complemented with missing information and saved,
        """
        if isinstance(base, SARSnapshot):
            base = self.service.getParent(uniqueId=base.uniqueId)
        liveValues = self.epics.get(base.getPVs())
        newLiveValues = {k: v for k, v in zip(base.getPVs(), liveValues)}
        if isinstance(base, SARConfig):
            if setValues is None:
                setValues = newLiveValues
            snap = {
                "uniqueId": -1,
                "dirty": True,
                "name": newName,
                "description": newDescription,
                "snapshotItems": [
                    _prep_input_for_snapshot_item(
                        configPv=o.get(),
                        unixSec=int(datetime.now().timestamp()),
                        pvValue=decodeValue(setValues.get(o.pvName, newLiveValues.get(o.pvName))),
                        pvType=decodeType(newLiveValues.get(o.pvName)),
                        # alarm=decodeAlarm(newLiveValues.get(o.pvName)), #  TODO see missing method
                        # display=decodeDisplay(newLiveValues.get(o.pvName)), # TODO see missing method
                        enumOptions=decodeEnum(newLiveValues.get(o.pvName)),
                    )
                    for o in base.configList
                ],
            }
            return SARSnapshot(**snap)
        else:
            raise NotImplementedError("Taking snapshots ONLY from the SarConfig for now (Work in Progress)!")

    def getSnapshot(self, snapshotId: str = None, snapshotName: str = None, sarItem: SARItem = None) -> SARSnapshot:
        """
        Returns one snapshot from the service selected by a provided unique ID
        :param sarItem: already existing object
        :param snapshotName: individual snapshot name
        :param snapshotId: individual snapshot ID
        :return: snapshot
        :raises ValueError if no snapshot found for the given snapshotId or snapshotName
        """
        if snapshotName is not None and snapshotId is not None and sarItem is not None:
            raise NotImplementedError("Cannot use both criteria (snapshotId or snapshotName)")
        if sarItem is not None and not sarItem.dirty:
            return self.service.getSarItem(sarItem.uniqueId)
        if snapshotId is not None:
            try:
                return self.service.getSarItem(snapshotId)
            except JSONDecodeError:
                warnings.warn("[pychiver:SaveRestore] Something went wrong with finding " "the provided snapshotId='{}'".format(snapshotId))
        if snapshotName is not None:
            allSnapshots = self.getAll()
            for one in allSnapshots.values():
                if snapshotName in one.name:
                    return self.getSnapshot(snapshotId=one.uniqueId)
        raise ValueError("Cannot find the snapshot for a provided snapshotId or snapshotName '{}'".format(snapshotName))

    def getSnapshots(self, config: SARConfig = None, configUniqueId: str = None) -> dict:
        """
        Returns all snapshots for a given config. Either config (SARConfig) or configUniqueId (str) needs to be provided

        :param config:
        :param configUniqueId:
        :return: a dict of SnapshotsName -> SARSnapshot
        """

        if config is not None and configUniqueId is not None:
            raise ValueError("You need to provide SARConfig or congfigUniqueId")

        if not isinstance(config, SARConfig) and configUniqueId is None:
            raise ValueError("Cannot find snapshots for not SARConfig")

        uniqueId = configUniqueId if configUniqueId is not None else config.uniqueId
        allInParentConfig = self.service.getChildren(uniqueId=uniqueId)
        toReturn = {}
        for one in allInParentConfig:
            toReturn[one["name"]] = self.service.getSarItem(one["uniqueId"])
        return toReturn

    def getSnapshotLocation(self, snapshot: SARSnapshot) -> tuple[SARFolder | SARConfig]:
        parentConfig = self.service.getParent(uniqueId=snapshot.uniqueId)
        deepestFolder = self.service.getParent(uniqueId=parentConfig.uniqueId)
        return deepestFolder, parentConfig

    def getCompositeSnapshot(self, snapshotId: str = None, snapshotName: str = None) -> SARCompositeSnapshot:
        """
        :return: a virtual snapshot
        """
        json = self.service.getCompositeSnapshotStub(snapshotId)
        snapshots = []
        for oneSnapshotId in json["referencedSnapshotNodes"]:
            a = self.service.getSarItem(oneSnapshotId)
            if isinstance(a, SARSnapshot):
                snapshots.append(a)
            else:
                aInception = self.getCompositeSnapshot(oneSnapshotId)
                for oneS in aInception.getSnapshots():
                    snapshots.append(oneS)
        return SARCompositeSnapshot(uniqueId=json["uniqueId"], name=json["name"], snapshots=snapshots)

    def getAll(self, useCache=False, nodeType=NodeType.SNAPSHOT) -> dict[str | SARSnapshot]:
        """
        Returns all snapshots found in the system. If useCache is True, it retrieves it from the local file.

        :param nodeType: default SNAPSHOT
        :param useCache: optional, default False
        :return:
        """
        configurations = {}
        if not useCache:
            self.service.getAllNodes(configurations, nodeType=nodeType)
            self._updateCache(configurations)
            return configurations
        else:
            # print(self.cachedConfigurations)
            return self.cachedConfigurations

    def getConfiguration(self, configId: str = None, configName: str = None) -> SARConfig:
        # TODO provide an easy way to search through the configurations (ie. without pulling all conf every time)
        # this has also a dedicated task the https://gitlab.esss.lu.se/ics-software/jmasar-service
        if configId is not None:
            item = self.service.getSarItem(configId)
            if isinstance(item, SARConfig):
                return item
        if configName is not None:
            for one in self.getAll(nodeType=NodeType.CONFIGURATION).values():
                if configName in one.name:
                    return self.getConfiguration(configId=one.uniqueId)

        raise ValueError("Given UniqueId {} is not for the configuration.".format(configId))

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
            # TODO add some comparator support
            values = self.epics.get(snapshot.getPVs())
            df["live_value"] = values
            df["archived_value"] = math.nan
            try:
                df["delta"] = df["stored_value"] - df["live_value"]
            except:
                warnings.warn("[pychiver:SaveRestore] Some error occurred during the delta calculation, skipping")

        if isinstance(date_time, datetime) or isinstance(date_time, str):
            if self._archiver is None:
                raise ValueError("Service not instantiated with the archiver link. Cannot perform that action!")
            date_time_to_consider = getDateTimeObj(date_time)
            # print(date_time_to_consider)
            startD = date_time_to_consider - timedelta(seconds=1)  # TODO archiver window to consider?
            endD = date_time_to_consider + timedelta(seconds=1)
            data = self._archiver.get(snapshot.getPVs(), start_date=startD, end_date=endD)
            # print("=======")
            # print(data)
            # print("=======")
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
        # TODO with the upcoming changes to SAR add additional flags to restore locally/remotely
        if not isinstance(snapshot, SARSnapshot):
            raise ValueError("For restore an SARSnapshot is required!")
        try:
            pvsToPut = [one.configPv["pvName"] for one in snapshot.getConfigPVs]
            valuesToPut = [one.value["value"] for one in snapshot.getConfigPVs]
            self.epics.put(pvsToPut, valuesToPut)
        except Exception:
            warnings.warn("[pychiver:SaveRestore] Something went wrong. Values were not set.")
            return 1
        return 0

    def save(self, sarItem: SARConfig | SARSnapshot | SARFolder | SARCompositeSnapshot, parentNodeId=None, debug=False):
        """
        Saves the locally created object to the service.

        NOTE: This requires to have an authenticated instance!

        :param debug: for Service calls debugging
        :param sarItem: The SaveRestore Object to persist in the service. Now supported Folders/Configs/Snapshots
        :param parentNodeId: The uniqueId of the parent node (folder/configuration)
        :return:
        """

        if isinstance(sarItem, SARConfig) and parentNodeId is None:
            raise ValueError("Cannot save Config without a parent!")

        if isinstance(sarItem, SARCompositeSnapshot) and parentNodeId is None:
            raise ValueError("Cannot save Composite Snapshot without the parent!")

        if isinstance(sarItem, SARSnapshot) and parentNodeId is None:
            parentNodeId = self.service.getParent(sarItem.uniqueId).uniqueId

        if isinstance(sarItem, SARSnapshot) and parentNodeId is not None and not sarItem.dirty:
            realParentId = self.service.getParent(sarItem.uniqueId).uniqueId
            if realParentId != parentNodeId:
                warnings.warn(
                    "[pychiver:SaveRestore] Given element parent's code ({}) "
                    "does not match the one given in the argument ({}), "
                    "using the actual parent code!".format(realParentId, parentNodeId)
                )
                parentNodeId = realParentId
        if self._username is None:
            warnings.warn("[pychiver:SaveRestore] Cannot save without authenticated username! Skipping")
        else:
            self.service.saveSarItem(sarItem=sarItem, parentId=parentNodeId, debug=debug)

    def _updateCache(self, newConfiguration):
        import copy

        self.cachedConfigurations = copy.deepcopy(newConfiguration)
        if self.cacheFile is not None:
            pickle.dump(self.cachedConfigurations, open(self.cacheFile, "wb+"))

    def _status(self):
        self.service.status()


# TODO MAKE THESE FEW ONES CLEANER for good. Duno yet how, but will need to be cleaner...
def decodeValue(value):
    if isinstance(value, ndarray):
        return value.tolist()
    elif isinstance(value, ntenum):
        return int(value)
    elif isinstance(value, ntwrappercommon):  # cover the p4p values
        return value.raw.value
    return value


def decodeType(value) -> dict:
    if isinstance(value, ntwrappercommon):  # cover the p4p types
        if isinstance(value, ntnumericarray):
            if "int" in str(value.dtype):
                return {"name": "VIntArray", "version": 1}
            return {"name": "VDoubleArray", "version": 1}
        elif isinstance(value, ntenum):
            return {"name": "VEnum", "version": 1}
        elif isinstance(value, ntfloat):
            return {"name": "VDouble", "version": 1}
        else:
            return {"name": "VDouble", "version": 1}
            # TODO add the remaining /types
    return type(value)


def decodeEnum(value):
    if isinstance(value, ntenum):
        return value.raw.value.choices
    return None


def decodeAlarm(value):
    return None


def decodeDisplay(value):
    return None
