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

from epicsarchiver import ArchiverAppliance
from epicsarchiver import ArchiveEvent

from .timeutils import validateTimeStampsReturnObjects, getDateTimeObj
from .codes import EpicsStatus, EpicsSeverity
from .domain import PVMetaInfo
from .calculations import Calculation, CalculationMode
from .instances import DEFAULT_MAX_EXTRACTION_SIZE, DEFAULT_ARCHIVER_CONF, DEFAULT_ARCHIVER_URL
from . import config

from enum import Enum
import pandas
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
        dataset["time"] = dataset.apply(lambda row: pandas.Timestamp(int(row["secs"]) * int(1e9) + int(row["nanos"]), tz=tz.UTC), axis=1)
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
            return PVDataType.DEFAULT.value


class ExpectedDataSizeExceedsLimitError(Exception):
    def __init__(self, expected_size, limit, pv):
        super().__init__()
        self.expected_size = expected_size
        self.limit = limit
        self.pv = pv

    def __str__(self):
        return (
            f"The expected datasize {self.expected_size} bytes exceeds the limit {self.limit}"
            f"bytes for pv {self.pv}. Set data_extraction_limit parameter to a higher value or None to force data extraction."
        )


class EndPointArchiver(EndPoint):
    """
    End point implementation for the ESS Archiver
    """

    def __init__(self, archiver_url=None):
        super().__init__(archiver_url)
        self.archiver_url_data = "{}:17668/retrieval/data/getData.json".format(archiver_url)
        self.archiver_url_mgmt = "{}:17665/mgmt/bpl".format(archiver_url)
        self.archiver_appliance = ArchiverAppliance(archiver_url.replace("http://", ""))

    def getDataForPV(
        self,
        PV,
        start_date,
        end_date=None,
        entries_limit=None,
        max_number_of_hours_back=24,
        data_extraction_limit=None,
        calc=Calculation.NTH,
        calc_mode=CalculationMode.TOTAL,
    ) -> pandas.DataFrame:
        status_details = self.getPVStatus(PV, info_type=PVMetaInfo.DETAILS)[PV]
        start_date, end_date = validateTimeStampsReturnObjects(start_date, end_date)
        expected_data_size = (
            PVDataType.getDataSizefromStringRepr(status_details["Archiver DBR type (from typeinfo):"])
            * int(status_details["Number of elements:"])
            * self._countEntries(PV, start_date, end_date)
        )
        if data_extraction_limit:
            if expected_data_size > data_extraction_limit:
                raise ExpectedDataSizeExceedsLimitError(expected_data_size, data_extraction_limit, PV)
        elif not data_extraction_limit and expected_data_size > DEFAULT_MAX_EXTRACTION_SIZE:
            warnings.warn(f"You are extracting {expected_data_size} bytes for pv {PV} it may take a while...")

        try:
            rawData = self._getRawRequest(
                PV, start_date, end_date=end_date, entries_limit=entries_limit, iteration=max_number_of_hours_back, calc=calc, calc_mode=calc_mode
            )
            # TODO think about putting the iterative search for an earlier value up to the Archiver class
            dataset = pandas.DataFrame(
                [
                    {"secs": event.timestamp.timestamp(), "val": event.val, "nanos": event.nanos, "severity": event.severity, "status": event.status}
                    for event in rawData
                ]
            )
            if dataset.empty:
                warnings.warn(f"Empty dataset extracted for '{PV}'")
                return dataset
            return _fix(dataset, start_date, end_date)
        except JSONDecodeError:
            warnings.warn("No data returned in the requested date range, returning empty dataset!")
            return self.getEmptyResult()

    def _getRawRequest(
        self, PV, start_date, end_date=None, entries_limit=5000, entries_warning_limit=5000, iteration=24, calc=Calculation.NTH, calc_mode=CalculationMode.TOTAL
    ) -> list[ArchiveEvent]:
        start_date, end_date = validateTimeStampsReturnObjects(start_date, end_date)
        entries = self._countEntries(PV, start_date, end_date)
        if not entries:
            config.printVerbose(f"No data found for '{PV}', trying earlier than: start:{start_date} until {end_date}")
        # TODO see if the recursive call should be here
        # TODO see if implicit calc def here is needed
        if entries_limit is None:
            entries_limit = max(entries, 1)
        if entries > entries_warning_limit:
            warnings.warn(f"You are about to extract {entries} samples, this operation may take significant amount of time...")
        nth = int(entries // entries_limit)
        if nth == 0:
            # warnings.warn(f"In the selected time range, the number of entries={entries} is under the specified limit={entries_limit}")
            nth = 1
        if calc != Calculation.NTH and calc_mode == CalculationMode.TOTAL:
            nth = int(2 * (end_date - start_date).total_seconds())  # strange way how archiver is doing the binning...
        if calc != Calculation.NTH and calc_mode == CalculationMode.BINNED:
            nth = entries_limit

        toReturn = self._get_data_request(PV, start_date, end_date, calc=calc, nth=nth)
        if not len(toReturn):
            if iteration > 0:
                return self._getRawRequest(
                    PV,
                    start_date=start_date - datetime.timedelta(hours=1),
                    end_date=start_date,
                    entries_limit=entries_limit,
                    iteration=iteration - 1,
                )
            else:
                warnings.warn("No data found (in the increased time window), returning empty result.")
                return []
        return toReturn

    def _get_data_request(self, PV, start_date: datetime, end_date: datetime, calc=Calculation.NTH, nth=1) -> list[ArchiveEvent]:
        func = calc.value.format(nth)
        return self.archiver_appliance.get_events(f"{func}({PV})", start_date, end_date)

    def _countEntries(self, PV, start_date: datetime, end_date: datetime) -> int:
        """
        Returns counted entries for the PV in a given time range.

        :param PV:
        :param start_date:
        :param end_date:
        :return:
        """
        res = self._get_data_request(PV, start_date, end_date, calc=Calculation.N_COUNT)
        entries = 0
        for i in res:
            entries += i.val
        return int(entries)

    def getPVStatus(self, PV: str | list, info_type=PVMetaInfo.STATUS, git_config_id=DEFAULT_ARCHIVER_CONF) -> dict:
        """
        :param info_type:
        :param git_config_id:
        :param PV:
        :return:
        """
        if git_config_id is None:
            git_config_id = DEFAULT_ARCHIVER_CONF
        if info_type is None:
            info_type = PVMetaInfo.STATUS
        if not isinstance(info_type, PVMetaInfo):
            raise ValueError("Type parameter of the wrong class! Use pychiver.domain.PVMetaInfo")

        if isinstance(PV, str):
            PV = [PV]
        status = {PV1: self.archiver_appliance.get_pv_status(PV1)[0] for PV1 in PV}
        if info_type == PVMetaInfo.STATUS:
            returnData = status
        elif info_type == PVMetaInfo.CONFIGURATION:
            warnings.warn("Warning: This may take some time, as all archive files will be scanned.")
            returnData = {}
            p = gitlab.Gitlab(DEFAULT_ARCHIVER_URL).projects.get(git_config_id)
            for pv in PV:
                returnData[pv] = {}
            for id, fn in [(f["id"], f["name"]) for f in p.repository_tree(path="files", get_all=True) if f["name"].endswith(".archive")]:
                all_pvs = [pv for pv in p.repository_raw_blob(id).decode().split("\n") if not pv.startswith("#") and not len(pv) == 0]
                for pv_in in returnData.keys():
                    if all_pvs.count(pv_in) > 0:
                        returnData[pv_in][fn] = all_pvs.count(pv_in)

        else:
            returnData = {}
            pvs = PV
            for onePV in pvs:
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
