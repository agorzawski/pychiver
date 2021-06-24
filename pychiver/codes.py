from enum import Enum, unique


@unique
class EpicsStatus(Enum):
    NO_ALARM = 0
    READ_ALARM = 1
    WRITE_ALARM = 2
    HIHI_ALARM = 3
    HIGH_ALARM = 4
    LOLO_ALARM = 5
    LOW_ALARM = 6
    STATE_ALARM = 7
    COS_ALARM = 8
    COMM_ALARM = 9
    TIMEOUT_ALARM = 10
    HWLIMIT_ALARM = 11
    CALC_ALARM = 12
    SCAN_ALARM = 13
    LINK_ALARM = 14
    SOFT_ALARM = 15
    BAD_SUB_ALARM = 16
    UDF_ALARM = 17
    DISABLE_ALARM = 18
    SIMM_ALARM = 19
    READ_ACCESS_ALARM = 20
    WRITE_ACCESS_ALARM = 21


@unique
class EpicsSeverity(Enum):
    NO_ALARM = 0
    MINOR = 1
    MAJOR = 2
    INVALID = 3
    EST_REPEAT = 3968
    REPEAT = 3856
    DISCONNECTED = 3904
    ARCHIVE_OFF = 3872
    ARCHIVE_DISABLED = 3848
