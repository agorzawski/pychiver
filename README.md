# py(ar)chiver

A python package providing a wrapped options for python access to the EPICS Archiver.

## Examples

### Get PV data
The simplest call is:
```python
from pychiver.archiver import Archiver

archiver = Archiver(archiver_url='http://archiver-01.tn.esss.lu.se:17668/retrieval/data/getData.json')

start = "2021-06-17 18:00:00"
end = "2021-06-20 12:00:00"
data = archiver.getDataSetForPV("RFQ-010:RFS-Kly-110:Oil-Tmp", start_date=start, end_date=end)
# return simple dataframe

pvs = ("RFQ-010:RFS-Kly-110:Oil-Tmp", "RFQ-010:RFS-Kly-110:Coll-WtrC-Flw")
data = archiver.getDataSetForPV(pvs, start_date=start, end_date=end)
# returns dict of PV -> dataframes
```
As it is `pandas` dataframe, one can do direct plots on it
```python
data.plot(x='time', y='val')
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

`make install`
or
`pip install`




