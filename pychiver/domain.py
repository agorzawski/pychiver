from enum import Enum, unique


@unique
class PVMetaInfo(Enum):
    INFO = 0
    STATUS = 1
    DETAILS = 2