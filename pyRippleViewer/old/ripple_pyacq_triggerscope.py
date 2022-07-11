# -*- coding: utf-8 -*-
# Copyright (c) 2016, French National Center for Scientific Research (CNRS)
# Distributed under the (new) BSD License. See LICENSE for more info.
"""
Noise generator node

Simple example of a custom Node class that generates a stream of random
values. 

"""
import yappi
from profiling_opts import runProfiler, LOGGING, logFormatDict

from datetime import datetime as dt
import os
import logging
import time
import pdb
from pathlib import Path

now = dt.now()

if LOGGING:
    pathHere = Path(__file__)
    thisFileName = pathHere.stem
    logFileDir = pathHere.resolve().parent.parent
    logFileName = os.path.join(
        logFileDir, 'logs',
        f"{thisFileName}_{now.strftime('%Y_%m_%d_%H%M')}.log"
        )
    logging.basicConfig(
        filename=logFileName,
        **logFormatDict
        )
    logger = logging.getLogger(__name__)

import pyRippleViewer
from pyRippleViewer import pyqtgraph as pg
from pyRippleViewer import ephyviewer as ephy
from pyRippleViewer import pyacq as pq
pyacq.QTriggeredOscilloscope
import sys

def wrapper():
    # Start Qt application
    app = pg.mkQApp()

    # Create a manager to spawn worker process to record and process audio
    # man = pyacq.create_manager()
    #
    # nodegroup_dev = man.create_nodegroup()
    # dev = nodegroup_dev.create_node(
    #     'XipppyBuffer', name='nip0')
    txBuffer = pyacq.XipppyTxBuffer(name='nip0_tx', dummy=True)
    #
    requestedChannels = {
            # 'hi-res': [],
            'hifreq': [2, 4],
            # 'stim': [chIdx for chIdx in range(0, 32, 3)],
            }

    txBuffer.configure(
        sample_interval_sec=500e-3, sample_chunksize_sec=100e-3,
        buffer_size_sec=5.,
        channels=requestedChannels, verbose=False, debugging=False)
    print(f'txBuffer.present_analogsignal_types = {txBuffer.present_analogsignal_types}')
    for signalType in pyacq.ripple_signal_types:
        txBuffer.outputs[signalType].configure(
            protocol='tcp', interface='127.0.0.1', transfermode='sharedmem', double=True
            # protocol='tcp', interface='127.0.0.1', transfermode='plaindata', double=True
            )
    txBuffer.initialize()

    showSpikes = False
    showScope = True
    showTFR = False
    signalTypesToPlot = ['hifreq'] # ['hi-res', 'hifreq', 'stim']

    # create a converter
    converter = pyacq.RippleStreamAdapter()
    converter.configure()
    converter.inputs['signals'].connect(txBuffer.outputs['hifreq'])
    converter.inputs['events'].connect(txBuffer.outputs['stim'])
    for signalType in ['signals', 'events']:
        converter.outputs[signalType].configure(protocol='inproc', transfermode='plaindata')
    converter.initialize()

    # Create a triggered oscilloscope to display data.
    viewer = pyacq.QDigitalTriggeredOscilloscope()
    viewer.configure(with_user_dialog=True)
    for signalType in ['signals', 'events']:
        viewer.inputs[signalType].connect(converter.outputs[signalType])
    viewer.initialize()
    viewer.show()
    viewer.params['decimation_method'] = 'min_max'
    viewer.by_channel_params['ch0', 'gain'] = 1.1
    viewer.by_channel_params['ch1', 'gain'] = 0.9
    #print(viewer.by_channel_params.keys())
    viewer.triggeraccumulator.params['stack_size'] = 1
    viewer.triggeraccumulator.params['left_sweep'] = -.2
    viewer.triggeraccumulator.params['right_sweep'] = .5
    # start nodes
    txBuffer.start()
    converter.start()
    viewer.start()
    


    if __name__ == '__main__':
        if sys.flags.interactive == 0:
            pg.exec()

if __name__ == '__main__':
    if runProfiler:
        import pyRippleViewer.profiling.profiling as prf
        from datetime import datetime as dt
        dateStr = dt.now().strftime('%Y%m%d%H%M')
        profilerResultsFileName = '{}_{}'.format(
            dateStr, __file__.split('.')[0])
        prf.profileFunction(
            topFun=wrapper,
            modulesToProfile=[pq],
            outputBaseFolder='../line_profiler_outputs',
            namePrefix=profilerResultsFileName, nameSuffix=None,
            outputUnits=1., minimum_time=1e-1,
            verbose=False, saveTextOnly=True)
    else:
        wrapper()