import datetime
from . import config


def find_same(
    data,
    base=None,
    against=None,
    margin_seconds=2,
    value_up=1,
    value_down=0,
) -> dict:
    """
    First implementation, ported from the jupyter run analysis notebooks (AG).

    It returns a dict of timestamps to detail for every timestamp the BASE PV changes its value from value_up->value_down.
    The details contain the info where AGAINST PV (all part of data object) changes along (same change value_up>down),
    how long it stays until the BASE value_down -> value_up etc, is it considered by common etc.

    :param base: the PV to be treated as the baseline, i.e. as the one that's evolution will trigger the comparison with the others
    :param against: the PV that should be checked after baseline has its change
    :param value_up: value considered to be high, default 1,
    :param value_down: value considered to be low, default 0,
    :param data: the pychiver.get(manyPVs) dict -> DataFrame,
    :param margin_seconds: the margin in withing the change is considered te same, default 2s
    :return: dict of timestamps to detail object (dict)
    """
    if base is None or against is None:
        raise ValueError('One needs to specify both the BASE and AGAINST PV')
    tmpResult = {}
    tempDFa = data[base]
    tempDFc = data[against]
    config.printVerbose(list(tempDFc.val))
    a = tempDFa.loc[tempDFa["val"] == value_down]
    aEnd = tempDFa.loc[tempDFa["val"] == value_up]
    c = tempDFc.loc[tempDFc["val"] == value_down]
    config.printVerbose(a.secs_nanos.to_numpy())
    config.printVerbose(aEnd.secs.to_numpy())
    config.printVerbose(c.secs_nanos.to_numpy())

    saved = []
    for one in c["secs_nanos"].values:
        for second in a["secs_nanos"].values:
            config.printVerbose(one, second, one - second)
            if abs(one - second) < margin_seconds:
                saved.append(second)

    config.printVerbose("Common FAILING saved: ", saved)
    config.printVerbose("-")
    config.printVerbose(a.secs.to_numpy())
    config.printVerbose((aEnd.secs.to_numpy()))
    config.printVerbose("-")
    if len(aEnd["secs_nanos"].values) > 0 and len(a["secs_nanos"].values) > 0:
        for ts1, ts2 in (
            zip(a["secs_nanos"].values, aEnd["secs_nanos"].values)
            if a["secs_nanos"].values[0] < aEnd["secs_nanos"].values[0]
            else zip(aEnd["secs_nanos"].values[1:], a["secs_nanos"].values)
        ):
            ts1DT = datetime.datetime.fromtimestamp(ts1)
            ts2DT = datetime.datetime.fromtimestamp(ts2)
            diff = ts2DT - ts1DT
            if diff < datetime.timedelta():
                diff = ts1DT - ts2DT
            save = True
            if save:
                tmpResult[ts1] = {
                    "start": ts1DT,
                    "end": ts2DT,
                    "duration": diff,
                    "common": ts1 in saved or ts2 in saved,
                    "stateOK": False,
                    "ts1": ts1,
                    "ts2": ts2,
                }
    else:
        config.printVerbose("Skip due to the no GBP missing")
    return tmpResult
