# Examples *Save and Restore*
> **NOTE**: Check `examples`, where interactive notebooks are.

To set up the client, all one needs is the following call:
```python
from pychiver.saveandrestore import SaveAndRestore
sar = SaveAndRestore(service_url="http://jmasar.tn.esss.lu.se")
```

To get all configuration Nodes:
```python
configurations = sar.getConfigurations()
# returns a dict of NameOfConfig to Configuration
```

To get all snapshots for a given configuration:

```python
sar.getSnapshots(configName='NameOfConfig')
# returns a dict of snapshot name to DataFrame with snapshot values
```
To compare:
```python
status = sar.compare(snapshot=some_snapshot)
#returns pandas.DataFrame with setPoint values and current values and with deltas
```
To restore:
```python
# TODO WIP still under implementation
status = sar.restore(snapshot=some_snapshot)
#returns 0 if all restored, rises ValueError, EpicsError in case of problems
```
To create new snapshot:
```python
sar.save(config=some_config, snapshot=some_snapshot, new_name='SomeNewName')
# TODO WIP still under implementation
```