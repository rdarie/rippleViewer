# -*- coding: utf-8 -*-
# Copyright (c) 2016, French National Center for Scientific Research (CNRS)
# Distributed under the (new) BSD License. See LICENSE for more info.
"""
Noise generator node

Simple example of a custom Node class that generates a stream of random
values. 

"""

from pyRippleViewer import runProfiler
'''
from datetime import datetime as dt
import os
import logging
now = dt.now()
logging.basicConfig(
    filename='..\logs\{}_{}.log'.format(
        os.path.splitext(__file__)[0], now.strftime('%Y%m%d%H%M')),
    level=logging.INFO)
'''
import sys
import pyacq as pq
import pyqtgraph as pg
import ephyviewer as ephy
import neurotic
import pdb, re
import time
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

showSpikes = False
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
    name='nip_rx0', max_xsize=12.)
rxBuffer.configure()
for signalType in pq.ripple_signal_types:
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
        traceview = ephy.TraceViewer(
            useOpenGL=False,
            source=sig_source, name='signal_{}'.format(signalType))
        traceview.params['scale_mode'] = 'by_channel'
        traceview.params['display_labels'] = True
        traceview.auto_scale()
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
    if signalType not in pq.ripple_event_types:
        continue
    if signalType not in rxBuffer.sources:
        continue
    sig_source = rxBuffer.sources[signalType]
    if showSpikes:
        spkview = ephy.SpikeTrainViewer(
            useOpenGL=False,
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
'''
for i, spike_source in enumerate(sources['spike']):
    view = SpikeTrainViewer(source=spike_source, name='spikes')
    ephyWin.add_view(view)

for i, ep_source in enumerate(sources['epoch']):
    view = EpochViewer(source=ep_source, name='epochs')
    ephyWin.add_view(view)

if 'event' in sources and len(sources['event']) > 0:
    ev_source_list = sources['event']
else:
    ev_source_list = sources['epoch']
for i, ev_source in enumerate(ev_source_list):
    view = EventList(source=ev_source, name='Event list')
    ephyWin.add_view(view, location='bottom',  orientation='horizontal')
'''
ephyWin.show()

if __name__ == '__main__':
    if sys.flags.interactive == 0:
        if runProfiler:
            from datetime import datetime as dt
            import os
            now = dt.now()
            dateStr = now.strftime('%Y%m%d')
            timeStr = now.strftime('%H%M')
            profilerResultsFileName = '{}_{}_pid_{}'.format(
                __file__.split('.')[0], timeStr, os.getpid())
            profilerResultsFolder = '../yappi_profiler_outputs/{}'.format(dateStr)
            ##
            import yappi, time
            yappiClockType = 'cpu'
            yappi.set_clock_type(yappiClockType) # Use set_clock_type("wall") for wall time
            yappi.start()
            start_time = time.perf_counter()
        ######################
        app.exec_()
        ######################
        if runProfiler:
            yappi.stop()
            stop_time = time.perf_counter()
            run_time = stop_time - start_time
            ##
            minimum_time = 1e-1
            modulesToPrint = []  # [pq, ephyviewer]
            runMetadata = {}
            from pyRippleViewer.profiling import profiling as prf
            prf.processYappiResults(
                fileName=profilerResultsFileName, folder=profilerResultsFolder,
                minimum_time=minimum_time, modulesToPrint=modulesToPrint,
                run_time=run_time, metadata=runMetadata)