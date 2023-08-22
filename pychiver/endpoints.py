"""
ESS 2021
Authors:
    A.Gorzawski <arek.gorzawski@ess.eu>
    E.Laface    <emmanuele.laface@ess.eu>
    B.Bolling   <benjamin.bolling@ess.eu>
"""
import datetime
from dateutil import tz
import warnings

warnings.formatwarning = lambda msg, *args, **kwargs: f"{msg}\n"  # Monkey-patching to remove line of source code
from json import JSONDecodeError

from .timeutils import validateTimeStamps, validateTimeStampsReturnObjects, getDateTimeObj
from .codes import EpicsStatus, EpicsSeverity
from .domain import PVMetaInfo
from .instances import DEFAULT_MAX_EXTRACTION_SIZE, DEFAULT_ARCHIVER_CONF
from . import config

from enum import Enum
import pandas
import json
import requests
import gitlab


class EndPoint:
    """
    Abstract end point implementation for the Archiver
    """

    def __init__(self, archiver_url=None):
        self.archiver_url = archiver_url
        if self.archiver_url is None:
            raise ValueError("Cannot instantiate Archiver without a proper link to the service.")

    def getDataForPV(self, PV: str, start_date, end_date=None, entries_limit=None) -> pandas.DataFrame:
        raise NotImplementedError("Abstract implementation called, use concrete ones.")

    def getPVStatus(self, PV):
        raise NotImplementedError("Abstract implementation called, use concrete ones.")

    def getEmptyResult(self):
        raise NotImplementedError("Abstract implementation called, use concrete ones.")


def _fix(dataset: pandas.DataFrame, start_date, end_date) -> pandas.DataFrame:
    """
    Fixes the data set when only ONE data point is extracted, by creating 'fake' two points of the same value at the
    boundary of the requested time span.

    NOTE: This fix ONLY applies for the scalars, if single data point as waveform is extracted, the fix is skipped!

    :param dataset:
    :param start_date:
    :param end_date:
    :return:
    """

    def _append_data():
        dataset["status_label"] = dataset.apply(lambda row: EpicsStatus(row["status"]), axis=1)
        dataset["severity_label"] = dataset.apply(lambda row: EpicsSeverity(row["severity"]), axis=1)
        dataset["secs_nanos"] = dataset["secs"] + dataset["nanos"] / 1e9
        dataset["time"] = pandas.to_datetime(dataset["secs_nanos"], unit="s")
        dataset["time_dt"] = dataset.apply(lambda row: datetime.datetime.utcfromtimestamp(row["secs_nanos"]).replace(tzinfo=tz.UTC), axis=1)

    if len(dataset) < 2:
        if len(dataset) and isinstance(dataset["val"][0], list):
            _append_data()
            return dataset

        from .calculations import LinearInterpolationStrategy

        warnings.warn("No value found in the the initial Time range, search extended to the earlier 24h.")

        new_times = [getDateTimeObj(start_date).timestamp(), getDateTimeObj(end_date).timestamp()]
        lis = LinearInterpolationStrategy(new_times)
        new_values = lis.getValues(dataset["secs"].values, dataset["val"].values)
        status = dataset["status"].values[-1]
        severity = dataset["severity"].values[-1]
        dataset.drop(dataset.index, inplace=True)
        dataset = pandas.concat(
            [
                dataset,
                pandas.DataFrame(
                    {
                        "val": new_values,
                        "secs": new_times,
                        "status": [status] * len(new_values),
                        "nanos": [0] * len(new_values),
                        "severity": [severity] * len(new_values),
                    }
                ),
            ],
            ignore_index=True,
        )

    _append_data()
    return dataset


class PVDataType(Enum):
    """
    Simple enum of available archiver types into size in bytes.
    """

    DBR_SCALAR_DOUBLE = 8
    DBR_SCALAR_ENUM = 1
    DEFAULT = 8

    @staticmethod
    def getDataSizefromStringRepr(pv_data_type: str) -> int:
        if pv_data_type in "DBR_SCALAR_DOUBLE":
            return PVDataType.DBR_SCALAR_DOUBLE.value
        if pv_data_type in "DBR_SCALAR_ENUM":
            return PVDataType.DBR_SCALAR_ENUM.value
        else:
            raise PVDataType.DEFAULT.value


class ExpectedDataSizeExceedsLimitError(Exception):
    def __init__(self, expected_size, limit, pv):
        super().__init__()
        self.expected_size = expected_size
        self.limit = limit
        self.pv = pv

    def __str__(self):
        return (
            f"The expected datasize {self.expected_size} bytes exceeds the limit {self.limit}"
            "bytes for pv {self.pv}. Set data_extraction_limit parameter to a higher value or None to force data extraction."
        )


class JsonEndPointArchiver(EndPoint):
    """
    JSON end point implementation for the ESS Archiver
    """

    def __init__(self, archiver_url=None):
        super().__init__(archiver_url)
        self.archiver_url_data = "{}:17668/retrieval/data/getData.json".format(archiver_url)
        self.archiver_url_mgmt = "{}:17665/mgmt/bpl".format(archiver_url)

    def getDataForPV(self, PV, start_date, end_date=None, entries_limit=None, max_number_of_hours_back=24, data_extraction_limit=None) -> pandas.DataFrame:
        status_details = self.getPVStatus(PV, info_type=PVMetaInfo.DETAILS)[PV]
        start_date_str, end_date_str = validateTimeStamps(start_date, end_date)
        expected_data_size = (
            PVDataType.getDataSizefromStringRepr(status_details["Archiver DBR type (from typeinfo):"])
            * int(status_details["Number of elements:"])
            * self._countEntries(PV, start_date_str, end_date_str)
        )
        if data_extraction_limit:
            if expected_data_size > data_extraction_limit:
                raise ExpectedDataSizeExceedsLimitError(expected_data_size, data_extraction_limit, PV)
        elif not data_extraction_limit and expected_data_size > DEFAULT_MAX_EXTRACTION_SIZE:
            warnings.warn(f"You are extracting {expected_data_size} bytes for pv {PV} it may take a while...")

        try:
            jsonReturn = self._getJSONRequest(PV, start_date, end_date=end_date, entries_limit=entries_limit, iteration=max_number_of_hours_back)
            # TODO think about putting the iterative search for an earlier value up to the Archiver class
            json_data = jsonReturn["data"]
            dataset = pandas.read_json(json.dumps(json_data))
            if dataset.empty:
                warnings.warn(f"Empty dataset extracted for '{PV}'")
                return dataset
            return _fix(dataset, start_date, end_date)
        except JSONDecodeError:
            warnings.warn("No data returned in the requested date range, returning empty dataset!")
            return self.getEmptyResult()

    def _getJSONRequest(self, PV, start_date, end_date=None, entries_limit=5000, entries_warning_limit=5000, iteration=24) -> dict:
        start_date_str, end_date_str = validateTimeStamps(start_date, end_date)
        start_date, end_date = validateTimeStampsReturnObjects(start_date, end_date)
        entries = self._countEntries(PV, start_date_str, end_date_str)
        if not entries:
            config.printVerbose(f"No data found for '{PV}', trying earlier than: start:{start_date} until {end_date}")
        # TODO see if the recursive call should be here
        if entries_limit is None:
            entries_limit = max(entries, 1)
        if entries > entries_warning_limit:
            warnings.warn(f"You are about to extract {entries} samples, this operation may take significant amount of time...")
        nth = int(entries // entries_limit)
        if nth == 0:
            warnings.warn(f"In the selected time range, the number of entries={entries} is under the specified limit={entries_limit}")
            nth = 1
        nth_url = f"{self.archiver_url_data}?pv=nth_{nth}({PV})&from={start_date_str}&to={end_date_str}"

        toReturn = requests.get(nth_url).json()
        if not len(toReturn) or not len(toReturn[0].get("data", [])):
            if iteration > 0:
                return self._getJSONRequest(
                    PV,
                    start_date=start_date - datetime.timedelta(hours=1),
                    end_date=start_date,
                    entries_limit=entries_limit,
                    iteration=iteration - 1,
                )
            else:
                warnings.warn("No data found (in the increased time window), returning empty result.")
                return {"data": []}
        return toReturn[0]

    def _countEntries(self, PV, start_date, end_date) -> int:
        """
        Returns counted entries for the PV in a given time range

        :param PV:
        :param start_date:
        :param end_date:
        :return:
        """
        count_url = f"{self.archiver_url_data}?pv=count({PV})&from={start_date}&to={end_date}"
        res = requests.get(count_url)
        if res.status_code != 200:
            raise ValueError(f"Failed to count entries for {PV}, status {res.status_code}")
        json_data = res.json()[0]["data"]
        entries = 0
        for i in json_data:
            entries += i["val"]
        return int(entries)

    def getPVStatus(self, PV, info_type=PVMetaInfo.STATUS, config_url=DEFAULT_ARCHIVER_CONF) -> dict:
        """
        :param info_type:
        :param config_url:
        :param PV:
        :return:
        """
        if not isinstance(info_type, PVMetaInfo):
            raise ValueError("Type parameter of the wrong class! Use pychiver.domain.PVMetaInfo")
        if isinstance(PV, str):
            PV = (PV,)
        url_to_check = f"{self.archiver_url_mgmt}/getPVStatus?pv={','.join(PV)}"
        status = requests.get(url_to_check).json()
        status = {statusItem["pvName"]: statusItem for statusItem in status}
        if info_type == PVMetaInfo.STATUS:
            returnData = status
        elif info_type == PVMetaInfo.CONFIGURATION:
            warnings.warn("Warning: This may take some time, as all archive files will be scanned.")
            returnData = {}
            p = gitlab.Gitlab("https://gitlab.esss.lu.se").projects.get(config_url)
            for pv in PV:
                returnData[pv] = {}
            for id, fn in [(f["id"], f["name"]) for f in p.repository_tree(path="files", get_all=True) if f["name"].endswith(".archive")]:
                all_pvs = [pv for pv in p.repository_raw_blob(id).decode().split("\n") if not pv.startswith("#") and not len(pv) == 0]
                for pv_in in returnData.keys():
                    if all_pvs.count(pv_in) > 0:
                        returnData[pv_in][fn] = all_pvs.count(pv_in)

        else:
            returnData = {}
            for onePV in PV:
                if "Not" in status[onePV]["status"]:
                    returnData[onePV] = status[onePV]
                else:
                    if info_type == PVMetaInfo.INFO:
                        # this end point does not support list
                        query = "getPVTypeInfo"
                    elif info_type == PVMetaInfo.DETAILS:
                        query = "getPVDetails"
                    else:
                        raise ValueError(f"Wrong PV status type {info_type}")
                    r = requests.get(f"{self.archiver_url_mgmt}/{query}?pv={onePV}")
                    if r.status_code == 200:
                        data = r.json()
                        if isinstance(data, list):  # Details is given as list..
                            returnData[onePV] = {item["name"]: item["value"] for item in data}
                        else:
                            returnData[onePV] = data
                    else:  # TODO should probably no get here anymore?
                        returnData[onePV] = {"pvName": onePV, "status": "Not being archived"}
        return returnData

    def getEmptyResult(self):
        return pandas.DataFrame(columns=("time", "val", "status_label", "severity_label", "secs_nanos", "secs", "nanos", "status", "severity"))
