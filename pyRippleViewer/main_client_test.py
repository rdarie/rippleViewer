# -*- coding: utf-8 -*-
# Copyright (c) 2016, French National Center for Scientific Research (CNRS)
# Distributed under the (new) BSD License. See LICENSE for more info.
"""
Noise generator node

Simple example of a custom Node class that generates a stream of random
values. 

"""
import yappi
from profiling_opts import runProfiler, LOGGING

from datetime import datetime as dt
import os
import logging
import time

now = dt.now()

if LOGGING:
    logging.basicConfig(
        filename='..\logs\{}_{}.log'.format(
            os.path.splitext(os.path.basename(__file__))[0].replace('__', ''), now.strftime('%Y%m%d%H%M')),
        level=logging.INFO)
    logger = logging.getLogger(__name__)

import pyRippleViewer
from pyRippleViewer import pyqtgraph as pg
from pyRippleViewer import ephyviewer as ephy
from pyRippleViewer import pyacq as pq

import sys
import re
#

usage = """Usage:
    python pyacq_ripple_host.py [address]

# Examples:
python host_server.py tcp://10.0.0.100:5000
python host_server.py tcp://10.0.0.100:*
"""

if len(sys.argv) == 2:
    rpc_addr = sys.argv[1]
else:
    rpc_addr = 'tcp://127.0.0.1:5001'
    
if not re.match(r'tcp://(\*|([0-9\.]+)):(\*|[0-9]+)', rpc_addr):
    sys.stderr.write(usage)
    sys.exit(-1)

def main():
    try:
        showSpikes = True
        showScope = True
        showTFR = True
        showAnnotator = False
        signalTypesToPlot = ['hifreq'] # ['hi-res', 'hifreq', 'stim']

        # Start Qt application
        app = pg.mkQApp()

        # In host/process/thread 2: (you must communicate rpc_addr manually)
        client = pq.RPCClient.get_client(rpc_addr)

        # Get a proxy to published object; use this (almost) exactly as you
        # would a local object:
        txBuffer = client['nip0']

        rxBuffer = pq.XipppyRxBuffer(
            name='nip_rx0', max_xsize=24.,
            requested_signal_types=signalTypesToPlot
            )
        rxBuffer.configure()
        for signalType in signalTypesToPlot:
            rxBuffer.inputs[signalType].connect(txBuffer.outputs[signalType])
        rxBuffer.initialize()
        rxBuffer.start()

        ephyWin = pq.NodeMainViewer(
            node=rxBuffer, debug=False,
            speed=10.
            )

        firstSource = True
        for i, signalType in enumerate(signalTypesToPlot):
            if signalType not in pq.ripple_analogsignal_types:
                continue
            if signalType not in rxBuffer.sources:
                continue
            sig_source = rxBuffer.sources[signalType]
            if showScope:
                traceview = ephy.FastTraceViewer(
                    source=sig_source, name='signal_{}'.format(signalType))
                traceview.params['scale_mode'] = 'by_channel'
                traceview.params['display_labels'] = True
                traceview.auto_scale()
                traceview.params_controller.on_automatic_color(cmap_name='Set3')
            if showTFR:
                tfrview = ephy.TimeFreqViewer(
                    source=sig_source,
                    scaleogram_type='wavelet',
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
            if signalType not in pq.ripple_event_types:
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
        ####################
        stopTimer = pg.Qt.QtCore.QTimer(
            interval=200 * 1000, singleShot=True)
        stopTimer.timeout.connect(app.quit)
        stopTimer.start()
        ######################
        app.exec()
        ######################
    finally:
        print('closing server')
        client.close_server()

if runProfiler:
    dateStr = now.strftime('%Y%m%d')
    timeStr = now.strftime('%H%M')
    profilerResultsFileName = '{}_{}_pid_{}'.format(
        __file__.split('.')[0], timeStr, os.getpid())
    profilerResultsFolder = '../yappi_profiler_outputs/{}'.format(dateStr)
    ##
    yappiClockType = 'cpu'
    yappi.set_clock_type(yappiClockType) # Use set_clock_type("wall") for wall time
    yappi.start()
    start_time = time.perf_counter()

try:
    main()
finally:
    if runProfiler:
        yappi.stop()
        stop_time = time.perf_counter()
        run_time = stop_time - start_time
        ##
        minimum_time = 1e-1
        modulesToPrint = [pq, ephy, pg]  # [pq, ephyviewer]
        runMetadata = {}
        from pyRippleViewer.profiling import profiling as prf
        prf.processYappiResults(
            fileName=profilerResultsFileName, folder=profilerResultsFolder,
            minimum_time=minimum_time, modulesToPrint=modulesToPrint,
            run_time=run_time, metadata=runMetadata)