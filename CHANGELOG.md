##0.5.2
- bug fixed the entries limit handling
- bug fixed the empty dataframe handling


##0.5.1
- LastAcquiredValue interpolation strategy
- collectors with exposed two methods: getPV() and clear()
- ManyPVWaveformCollector

##0.5.0
- waveform collectors (Archiver and Realtime)

##0.4.0
- added first support for the save and restore
  - configuration/snapshots lists 
  - snapshot details
  - snapshot restore (WIP)

##0.3.1
- included description of the EPICS status codes
- included warning when extracting the waveforms

##0.3.0
- improved the `archiver.get()`
- introduced `archiver.getAligned()`
- PV status check `archiver.check()`
- moving average `archiver.getMovingAverage()`
- simplified init with a single url

##0.2.0
- simple get for one or many PVs
- abstraction for possible different implementations

##0.1.0
- initial import
- time stamps utils
