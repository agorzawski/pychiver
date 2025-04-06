from setuptools.sandbox import save_argvfrom zipfile import stringEndArchive

# Examples *Save and Restore*
> Disclaimer: **This is a prototype for the python service connection for save and restore service. Use at your own risk**
>
>This module is using `p4p` with `pva` to interact with epics network.


## Service

#### To set up the client, all one needs is the following call:
```python
from pychiver.saveandrestore import SaveAndRestore
sar = SaveAndRestore()
```

> there is `service_url` argument available, by default `pychiver.instances.DEFAULT_SAVE_RESTORE` is used.


#### To get information of all snapshots:

```python
snapshotsAll = sar.getAll()
# returns a dict of uniqueId to Snapshot
```

#### To get a specific configuration, snapshot or any specific/generic node:

```python
sar.getConfiguration(configId="1c5e67db-9b08-496f-85ec-8c1dc849e021")
sar.getSnapshot(snapshotId='5314e53b-b7c1-432c-b996-0733f28fd15c')
sar.getCompositeSnapshot(snapshotId='someId')
sar.getFolder(folderId='someOtherId')

# returns a node by name, if more than one found with the same name, it returns the most recent one.
sar.getConfiguration(configName="blah")
sar.getSnapshot(snapshotName='Some name of the snapshot')
sar.getCompositeSnapshot(snapshotName='Some name of the snapshot')
sar.getFolder(folderName='Some name of the folder')
```

or use the generic call
```python
sar.getNode(nodeId='someOtherId')
```

#### To get all snapshots for a given configuration:
> To get _a real_ `configUniqueId` (or any `uniqueId`) one can use Phoebus App and copy/paste it from there
```python
sar.getSnapshots(configUniqueId='configUniqueId')
# returns a dict of snapshot name to a SARSnapshot objects
```

#### To get folder content:
```python
sar.getFolderContent(folderId='someId')
# returns a dict of SARItem to SARItem objects representing the hierarchy
```
>**NOTE** it may be an expressive call if a folder contains many items, as it will fetch all items

### Actions (read)
>  the following works for the `some_snapshot` being `SARSnapshot` or `SARCompositeSnapshot`

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
from pychiver.instances import DEFAULT_ARCHIVER
from pychiver.saveandrestore import SaveAndRestore

sar = SaveAndRestore(archiver_url=DEFAULT_ARCHIVER)

status = sar.compare(snapshot=some_snapshot, date_time="2022-06-13 19:21:21")
```

Example of the returned dataframe:
```commandline
syslog:> Snapshot: MEBT magnets setting, all current up to 60 mA with right MEBT chopper voltage/0c6184dc-07bc-4124-9519-7667c028ee7c  GOLDEN
syslog:> check state on: 2022-06-13 19:21:21

                           pv_name  stored_value  archived_value
0     MEBT-010:PwrC-PSCH-001:Cur-S         -3.75          -0.600
1     MEBT-010:PwrC-PSCH-002:Cur-S          6.50           5.000
2     MEBT-010:PwrC-PSCH-003:Cur-S         -1.50          -0.350
3     MEBT-010:PwrC-PSCH-004:Cur-S          0.00          -0.300
4     MEBT-010:PwrC-PSCH-005:Cur-S          0.00           0.030
5     MEBT-010:PwrC-PSCH-006:Cur-S          0.00           0.080
6     MEBT-010:PwrC-PSCH-007:Cur-S          0.00           0.200
7     MEBT-010:PwrC-PSCV-001:Cur-S         -6.75          -6.000
8     MEBT-010:PwrC-PSCV-002:Cur-S          9.25           7.000
9     MEBT-010:PwrC-PSCV-003:Cur-S         -2.00          -1.380
10    MEBT-010:PwrC-PSCV-004:Cur-S          0.00          -0.370
11    MEBT-010:PwrC-PSCV-005:Cur-S          0.00          -1.000
12    MEBT-010:PwrC-PSCV-006:Cur-S          0.00          -1.078
13    MEBT-010:PwrC-PSCV-007:Cur-S          0.00           1.630
14    MEBT-010:PwrC-PSQH-002:Cur-S        120.27         117.408
15    MEBT-010:PwrC-PSQH-004:Cur-S          0.00          29.206
16    MEBT-010:PwrC-PSQH-005:Cur-S          0.00          40.333
17    MEBT-010:PwrC-PSQH-007:Cur-S          0.00          56.432
18    MEBT-010:PwrC-PSQV-001:Cur-S        101.08          97.141
19    MEBT-010:PwrC-PSQV-003:Cur-S         80.00          74.454
20    MEBT-010:PwrC-PSQV-006:Cur-S          0.00          88.039
21  MEBT-010:BMD-Chop-001:Field-SP       4500.00             NaN
```
### Action to restore:

> **NOTE** the restore (pvput) action is executed where the client package is running. **You may not have a privilege** (due to the network configuration) to successfully execute your call.

>  the following works for the `some_snapshot` being `SARSnapshot` or `SARCompositeSnapshot`

```python
status = sar.restore(snapshot=some_snapshot)
#returns 0 if all restored, rises ValueError, EpicsError in case of issues
```

### Actions to create, take and/or interact (authentication needed!)
> General  note: All snapshots created, taken and/or manipulated via the following have flag `dirty=True` to signal that they are NOT the service copy

#### To create a folder

```python
from pychiver.sardomain import SarItemBuilder
folder = SarItemBuilder.getInstance().createFolder(name, description)
```


#### To create a config

```python
from pychiver.sardomain import SarItemBuilder

some_config = SarItemBuilder.getInstance().createConfiguration(
  sarConfigPVs=[SARConfigPV(pvName="SomePV1", readbackPvName="SomePV1-RB")),
                SARConfigPV(pvName="SomePV2"),
                SARConfigPV(pvName="SomePV3")],
  name="Configuration created via python package",
  description="Some needed description")

```
#### Take a new snapshot:


```python
# live values
some_snapshot_retake = sar.takeSnapshot(some_config,
                                        newName="Values After setup",
                                        newDescription="Feb2024")

# (otional) prepare with fixed SetPoint values
setValues = {"SomePV1": 10.0, "SomePV2": 112.0, "SomePV3": "Disabled",}
# (optiona) prep with fixed Readback values (if applicable)
setReadbackValues = {"SomePV1_RB": -1.0}

some_snapshot = sar.takeSnapshot(some_config, # see example above!
                                 setValues=setValues, # if this optional argument is not given, live values are used!
                                 setReadbackValuest=setReadbackValues, # if this optional argument is not given, live values are used!
                                 newName="Values From the DB",
                                 newDescription="from the tests back on Nov2023")
```

> NOTE: for the `enum` type values can be either "string option" or int ordinal. Eg. 'Probe' or 1

> **NOTE:** All locally created SAR items are _"dirty=True"_ (in the console `[*]`) until the successful save operation is performed!

#### To create a composite snapshot

```python
from pychiver.sardomain import SarItemBuilder
snapshots = [snapshot1, snapshot2]
vSnapshot = SarItemBuilder.getInstance().createCompositeSnapshot(name, description, snapshots)
```


> **Note** at this call a live call (pvget) will be executed to establish types of PVs and their 'now' value(s)

> Note1: `setValues` does not have to be all PVs, in case user one `setValue` is not provided
> the one currently fetched from live epics is kept.
ś
> Note2: There is an ongoing development. Only main types of PVs: Scalar, Arrays (Double and Int), Enum
> are tested and working...


#### To SAVE the item in the service:

> Note: to interact with the service, one needs to authenticate:
```python
sar = SaveAndRestore(username="somename", password="somepass")

# or if you have an instance running, i.e. jupyter notebook

sar.authenticate(username="somename", password="somepass")
```

```python
folder = sar.save(sarItem=some_folder, parentNodeId='<folder uniqueId>')
#or
config = sar.save(sarItem=some_config, parentNodeId='<folder uniqueId>')
#or
snapshot = sar.save(sarItem=some_snapshot, parentNodeId='configUniqueId')
# or
compositeSnapshot = sar.save(sarItem=compositeSnapshot, parentNodeId='<folder uniqueId>')
```
> A successful save, updates the result with the correct `uniqueId` and sets `dirty=False`

> No virtual snapshots to be saved  yet via this package, this is deferred WIP.

## Domain

The main objects are:
- `SARConfig` - object that holds configurations for many PVs,
- `SARConfigPV` - simple configuration for one PV,
- `SARSnapshotItem` - snapshot item holding individual ConfigPV and its snapshoted value,
- `SARSnapshot` - snapshot that contains the stored SARSnapshotItems,
- `SARCompositeSnapshot` - virtual snapshot that holds provided snapshots' references and provides the
  combined actions (e.g. compare, restore) on all of them at once
