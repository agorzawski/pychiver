## Examples on *Archiver* utility classes for BOOLEAN PVs

More examples in `examples/Boolean signals.ipynb`

### init
To set up the client, one needs the following call:
```python
from pychiver.archiver import Archiver
archiver = Archiver(archiver_url='http://archiver-01.tn.esss.lu.se')
```


> **NOTE**: Providing PVS that are having values different from 0 and 1 will result in the exception

Select the what and the when:
```python
start = "2021-06-17 18:00:00"
end = "2021-06-20 12:00:00"
pvs = ("RFQ-010:RFS-VacMon-110:Status-Ilck-RB",  # vac 1
       "RFQ-010:RFS-VacMon-140:Status-Ilck-RB",  # vac 2
       "RFQ-010:RFS-FIM-101:RP1-Ilck-RB",  # reflected power 1
       "RFQ-010:RFS-FIM-101:RP2-Ilck-RB")  # reflected power 2
```

### compare for close occurrences

```python
comparison_result = archiver.compare(pvs, start, end,
                                     tolerance_in_seconds=0.15,
                                     compare_edge=Edge.FALLING)
```

As a result an array with timestamps matching the query is returned.
