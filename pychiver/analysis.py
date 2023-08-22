import datetime
from . import config


def find_same(data,
              base,
              against=None,
              margin_seconds=2,
              value_up=1,
              value_down=0,) -> dict:
    """
    First implementation, ported from the jupyter run analysis notebooks (AG).

    It returns a dict of timestamps, to detials for every time the base PV changes value_up->value_down. The details
    contain the info what other PV (part of data) goes along, how long takes value_down -> value up etc.

    :param value_up:
    :param value_down:
    :param data:
    :param base:
    :param against:
    :param margin_seconds:
    :param verbose:
    :return:
    """
    tmpResult = {}
    tempDFa = data[base]
    tempDFc = data[against]
    config.printVerbose(list(tempDFc.val))
    a = tempDFa.loc[tempDFa['val'] == value_down]
    aEnd = tempDFa.loc[tempDFa['val'] == value_up]
    c = tempDFc.loc[tempDFc['val'] == value_down]
    config.printVerbose(a.secs_nanos.to_numpy())
    config.printVerbose(aEnd.secs.to_numpy())
    config.printVerbose(c.secs_nanos.to_numpy())

    saved = []
    for one in c['secs_nanos'].values:
        for second in a['secs_nanos'].values:
            config.printVerbose(one, second, one-second)
            if abs(one - second) < margin_seconds:
                saved.append(second)

    config.printVerbose('Common FAILING saved: ', saved)
    config.printVerbose('-')
    config.printVerbose(a.secs.to_numpy())
    config.printVerbose((aEnd.secs.to_numpy()))
    config.printVerbose('-')
    if len(aEnd['secs_nanos'].values) > 0 and len(a['secs_nanos'].values) > 0:
        for ts1, ts2 in zip(a['secs_nanos'].values, aEnd['secs_nanos'].values) if a['secs_nanos'].values[0] < \
                                                                                  aEnd['secs_nanos'].values[0] else zip \
                    (aEnd['secs_nanos'].values[1:], a['secs_nanos'].values):
            ts1DT = datetime.datetime.fromtimestamp(ts1)
            ts2DT = datetime.datetime.fromtimestamp(ts2)
            diff = (ts2DT - ts1DT)
            if diff < datetime.timedelta():
                diff = (ts1DT - ts2DT)
            save = True
            if save:
                tmpResult[ts1] = {'start': ts1DT, 'end': ts2DT, 'duration': diff,
                                  'common': ts1 in saved or ts2 in saved, 'stateOK': False, 'ts1': ts1, 'ts2': ts2}
    else:
        config.printVerbose('Skip due to the no GBP missing')
    return tmpResult
