# py(ar)chiver
> **DISCLAIMER**: This is an advanced prototype but still some bugs can occur

A python package providing a wrapped service options:
- **for archived data access** in the *EPICS Archiver*.
  - Simple **data extraction** for scalars and waveforms,
  - **Auto search for the last value** if not found in the requested time window,
  - Some tools are provided for **data processing**  like data aligning, moving average or data source (PVs) status checks.
- **for saved configurations and snapshots** in the EPICS *SaveAndRestore*, see more in [SAVEANDRESTORE.md](SAVEANDRESTORE.md)
- Extended **waveform support** with collectors for both: archiver and realtime subscriptions, see more in [WAVEFORM.md](WAVEFORM.md)
> **NOTE**: Check folder `examples`, where interactive notebooks and cli scripts are.

## Examples on *Archiver* in nutshell

To set up the client, all one needs is the following call:
```python
from pychiver.archiver import Archiver
archiver = Archiver(archiver_url='http://archiver-01.tn.esss.lu.se')
```
Specify what and from when is going to be extracted
```python
start = "2021-06-17 18:00:00"
end = "2021-06-20 12:00:00"
pvs = ("RFQ-010:RFS-Kly-110:Oil-Tmp", "RFQ-010:RFS-Kly-110:Coll-WtrC-Flw")
```
### Get PV data

Regardless if it is a scalar or waveform:
```python
data = archiver.get(pvs, start_date=start, end_date=end)
# returns dict of PV -> DataFrame
```

### Get more PVS at once and align them together

```python
data = archiver.getAligned(pvs, start_date=start, end_date=end)
#returns one combined pandas DataFrame with all PVS aligned to the desired time_base
```
> **NOTE**: this will only work for scalars! An exception will be thrown if you will mix waveforms and scalars

### Get PV Status
```python
data = archiver.check("RFQ-010:RFS-Kly-110:Oil-Tmp")
# returns details of the PVs within the archiver
```

```python
{'RFQ-010:RFS-Kly-110:Oil-Tmp': {'lastRotateLogs': 'Never',
  'appliance': 'archiver-01',
  'pvName': 'RFQ-010:RFS-Kly-110:Oil-Tmp',
  'pvNameOnly': 'RFQ-010:RFS-Kly-110:Oil-Tmp',
  'connectionState': 'true',
  'lastEvent': 'Jun/24/2021 19:35:05 +02:00',
  'samplingPeriod': '0.07',
  'isMonitored': 'true',
  'connectionLastRestablished': 'Never',
  'connectionFirstEstablished': 'Jun/21/2021 12:20:38 +02:00',
  'connectionLossRegainCount': '0',
  'status': 'Being archived'}}
```


## TimeStamp Format
*pychiver* supports the following formats:
1) as `datetime` objects, eg:  `datetime.now()`, `datetime.strptime('2021-02-28 13:13:13', DATE_FORMAT)`
1) as plain text e.g. `'2021-02-28 13:13:13'`, following the format `%Y-%m-%d %H:%M:%S`


# Installation

```commandline
$ git clone <repo_url/pychiver>
$ cd pychiver
$ pip install .
```
 
or 

TBD

## Extra environmental configuration
Setup of the environmental variable is possible, the following can be set for the desired instance
 - `EPICS_ARCHIVER_URL` 
 - `SAVE_AND_RESTORE_URL`




