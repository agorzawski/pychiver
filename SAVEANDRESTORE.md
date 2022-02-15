# Examples *Save and Restore*
> **NOTE**: Check `examples`, where interactive notebooks are.
>
> **This is a prototype for the python service connection for save and restore service.**

## Service

#### To set up the client, all one needs is the following call:
```python
from pychiver.saveandrestore import SaveAndRestore
sar = SaveAndRestore(service_url="http://jmasar.tn.esss.lu.se")
```

#### To get information of all nodes of given type:

```python
configurationsNamesAndIds = sar.getAll()
# returns a dict of NameOfConfig to Configuration (default is NodeType.CONFIGURATION)

snapshotsNamesAndIds = sar.getAll(nodeType=NodeType.SNAPSHOT)
# returns a dict of SnapshotName to Snapshot definition
```

#### To get all snapshots for a given configuration:

```python
sar.getSnapshots(configUniqueId='configUniqueId')
# returns a dict of snapshot name to a snapshot objects
```

#### To get a specific snapshot:
> NOTE: this call will raise `ValueError` if no snapshot is found!
```python
sar.getSnapshot(snapshotId='5314e53b-b7c1-432c-b996-0733f28fd15c')
# returns a snapshot

sar.getSnapshot(snapshotName='Some name of the snapshot')
# returns a snapshot, if more than one found with the same name, it returns the most recent one.
```

#### To create a virtual snapshot

```python
vSnapshot = sar.createVirtualSnapshot(self, name, snapshots)
```

### Actions
>  the following works for the `some_snapshot` being `SARSnapshot` or `SARVirtualSnapshot`

##### Live values - detailed
```python
status = sar.compare(snapshot=some_snapshot)
#returns pandas.DataFrame with setPoint values and current values and with deltas
```

##### Live values, simplified (True/False)
```python
status = sar.compareAndCheck(snapshot=some_snapshot)
#returns True or False
```

##### Archived values at given date:
>**NOTE** the service needs to be started with the additional, not empty parameter `archiver_url`
```python
from pychiver.saveandrestore import SaveAndRestore
sar = SaveAndRestore(service_url="http://jmasar.tn.esss.lu.se",
                     archiver_url="'http://archiver-01.tn.esss.lu.se'")
status = sar.compare(snapshot=some_snapshot, date_time="2021-07-01 21:21:21")
#returns pandas.DataFrame with setPoint values and current values and with deltas
```

#### To restore:

> **NOTE** the restore (pvput) action is executed where the client package is running. **You may not have a privilege** (due to the network configuration) to successfully execute your call.
```python
status = sar.restore(snapshot=some_snapshot)
#returns 0 if all restored, rises ValueError, EpicsError in case of problems
```

#### To take/ save new snapshot:
> **NOTE** WIP, not implemented yet

```python
some_snapshot = sar.takeSnapshot(config=some_config)
some_snapshot_retake = sar.takeSnapshot(snapshot=some_snapshot)
```

```python
sar.save(config=some_config, snapshotName='Some New Name for the Snapshot', comment='Some Comment')
#or
sar.save(snapshot=some_snapshot, nodeType=NodeType.SNAPSHOT)
#or
sar.save(snapshot=some_snapshot, nodeType=NodeType.VIRTUAL_SNAPSHOT)
```


## Domain

The main objects are:
- `SARConfig`
- `SARConfigPV`
- `SARSnapshot` - snapshot that contains the storred configurations
- `SARVirtualSnapshot` - virtual snapshot that holds provided snapshots' references and provides the
  combined actions (e.g. compare, restore) on all of them at once
