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
pq.QTriggeredOscilloscope
import sys

def wrapper():
    # Start Qt application
    app = pg.mkQApp()

    # Create a manager to spawn worker process to record and process audio
    # man = pq.create_manager()
    #
    # nodegroup_dev = man.create_nodegroup()
    # dev = nodegroup_dev.create_node(
    #     'XipppyBuffer', name='nip0')
    txBuffer = pq.XipppyTxBuffer(name='nip0_tx', dummy=True)
    #
    requestedChannels = {
            # 'hi-res': [2, 4],
            # 'hifreq': [2, 4],
            'stim': [chIdx for chIdx in range(0, 32, 5)],
            }

    txBuffer.configure(
        sample_interval_sec=100e-3, sample_chunksize_sec=100e-3,
        buffer_size_sec=5.,
        channels=requestedChannels, verbose=False, debugging=False)
    print(f'txBuffer.present_analogsignal_types = {txBuffer.present_analogsignal_types}')
    for signalType in pq.ripple_signal_types:
        txBuffer.outputs[signalType].configure(
            # protocol='inproc', transfermode='sharedmem', double=True
            protocol='tcp', interface='127.0.0.1', transfermode='plaindata', double=True
            )
    txBuffer.initialize()

    showSpikes = False
    showScope = True
    showTFR = False
    signalTypesToPlot = ['hifreq'] # ['hi-res', 'hifreq', 'stim']

    channel_info = txBuffer.outputs['hi-res'].params['channel_info']
    channel_group = {
        'channels': [idx for idx, item in enumerate(channel_info)],
        'geometry': [[0, 100 * idx] for idx, item in enumerate(channel_info)]
    }
    triggerAcc = pq.RippleTriggerAccumulator()
    triggerAcc.configure(channel_group=channel_group)
    
    triggerAcc.inputs['signals'].connect(txBuffer.outputs['hifreq'])
    triggerAcc.inputs['events'].connect(txBuffer.outputs['stim'])

    triggerAcc.initialize()
    win = pq.RippleTriggeredWindow(triggerAcc)
    win.show()
    
    # start nodes
    txBuffer.start()
    triggerAcc.start()
    #
    win.start_refresh()
    app.exec()

if __name__ == '__main__':
    wrapper()