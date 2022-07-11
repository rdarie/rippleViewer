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

from pyRippleViewer import *

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
            # 'hifreq': [2, 3, 12],
            # 'stim': [chIdx for chIdx in range(0, 32, 3)],
            }

    txBuffer.configure(
        sample_interval_sec=100e-3, sample_chunksize_sec=100e-3,
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
    showTFR = True
    signalTypesToPlot = ['hifreq'] # ['hi-res', 'hifreq', 'stim']
    rxBuffer = pyacq.XipppyRxBuffer(
        name='nip_rx0',
        requested_signal_types=signalTypesToPlot
        )
    rxBuffer.configure()
    for signalType in signalTypesToPlot:
        rxBuffer.inputs[signalType].connect(txBuffer.outputs[signalType])
    for signalType in pyacq.ripple_signal_types:
        rxBuffer.outputs[signalType].configure(
            protocol='tcp', interface='127.0.0.1', transfermode='sharedmem', double=True
            # protocol='tcp', interface='127.0.0.1', transfermode='plaindata', double=True
            )
    rxBuffer.initialize()

    ephyWin = pyacq.NodeMainViewer(
        node=rxBuffer, debug=False,
        speed=5.
        )

    firstSource = True
    for i, signalType in enumerate(signalTypesToPlot):
        if signalType not in pyacq.ripple_analogsignal_types:
            continue
        if signalType not in rxBuffer.sources:
            continue
        sig_source = rxBuffer.sources[signalType]
        if showScope:
            traceview = ephy.TraceViewer(
                source=sig_source, name='signal_{}'.format(signalType))
            traceview.params['scale_mode'] = 'by_channel'
            traceview.params['display_labels'] = True
            # traceview.auto_scale()
            traceview.params_controller.on_automatic_color(cmap_name='Set3')
        if showTFR:
            tfrview = ephy.TimeFreqViewer(
                source=sig_source,
                scaleogram_type='spectrogram',
                name='timefreq_{}'.format(signalType))
        if firstSource:
            ephyWin.set_time_reference_source(sig_source)
            if showScope:
                ephyWin.add_view(
                    traceview, connect_time_change=False,
                    )
            if showTFR:
                ephyWin.add_view(
                    tfrview, connect_time_change=False,
                    )
            firstSource = False
        else:
            if showScope:
                ephyWin.add_view(
                    traceview, connect_time_change=False,
                    tabify_with='signal_{}'.format(previousSignalType))
            if showTFR:
                ephyWin.add_view(
                    tfrview, connect_time_change=False,
                    tabify_with='timefreq_{}'.format(previousSignalType))
        previousSignalType = signalType

    firstSource = True
    for i, signalType in enumerate(signalTypesToPlot):
        if signalType not in pyacq.ripple_event_types:
            continue
        if signalType not in rxBuffer.sources:
            continue
        sig_source = rxBuffer.sources[signalType]
        if showSpikes:
            spkview = ephy.SpikeTrainViewer(
                source=sig_source, name='spikes_{}'.format(signalType))
            spkview.params_controller.on_automatic_color(cmap_name='Set3')
        if firstSource:
            if showSpikes:
                ephyWin.add_view(
                    spkview, connect_time_change=False,
                    )
            firstSource = False
        else:
            if showSpikes:
                ephyWin.add_view(
                    spkview, connect_time_change=False,
                    tabify_with='spikes_{}'.format(previousSignalType))
        previousSignalType = signalType

    ephyWin.show()
    # start nodes
    txBuffer.start()
    rxBuffer.start()
    ephyWin.start_viewers()

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