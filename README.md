# py(ar)chiver

A python package providing a wrapped options **for data access** in the EPICS Archiver.
Additionally, some tools are provided like data aligning, moving average or data source (PVs) status checks.

## Examples

To setup, all one needs is the following call:
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

```python
data = archiver.get(pvs, start_date=start, end_date=end)
# returns dict of PV -> dataframes
```

### Get more PVS at once and align them together

```python
data = archiver.getAligned(pvs, start_date=start, end_date=end)
#returns one combined pandas DataFrame with all PVS aligned to the desired time_base
```

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

### Get Waveform Data
```python
#TODO add example
```

### TimeStamp Format
*pychiver* supports the following formats:
1) as `datetime` objects, eg:  `datetime.now()`, `datetime.strptime('2021-02-28 13:13:13', DATE_FORMAT)`
1) as plain text e.g. `'2021-02-28 13:13:13'`, following the format `%Y-%m-%d %H:%M:%S`

## Extra configuration
Setup of the environmental variable is possible. 
`EPICS_ARCHIVER_URL` can be set to the desired instance.


## Installation

Enter the folder with the source

`make install`
or
`pip install .`




