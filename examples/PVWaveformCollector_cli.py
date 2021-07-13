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