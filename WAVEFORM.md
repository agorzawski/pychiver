# pychiver as WAVEFORM support

There are two implementations for waveform collectors:
* `PVWaveformCollector`
* `ArchiverWaveformCollector`

Both provide convenience methods for treating waveforms, their running scalar representations, ROI configuration etc.

## Archived PV collector

```python
start_time = "2021-06-25 12:00:00"
end_time = "2021-06-25 14:30:00"
PV = "RFQ-010:RFS-Kly-110:PwrFwd-Wave-PM"

from pychiver.waveform import ArchiverWaveformCollector
pvCollector = ArchiverWaveformCollector(PV=PV, 
                                        start_date=start_time, 
                                        end_date=end_time,
                                        archiver_url='http://archiver-01.tn.esss.lu.se')
print(pvCollector.getAllWaveforms())
```


## Real-time PVWaveform Collector

```python
from time import sleep
from pychiver.waveform import PVWaveformCollector


def update_plot(**kwargs):
    print("------ ({}) ------".format(kwargs.get('lastCheck')))
    print(kwargs.get('dataframe'), sep='\n')


pvCollector = PVWaveformCollector(PV="RFQ-010:RFS-EPR-110:Cur-Wave_",
                                  callback=update_plot,
                                  callback_delay_in_seconds=2)

while True:
    sleep(0.1)
```