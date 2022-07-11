# -*- coding: utf-8 -*-
# Copyright (c) 2016, French National Center for Scientific Research (CNRS)
# Distributed under the (new) BSD License. See LICENSE for more info.
"""
Noise generator node

Simple example of a custom Node class that generates a stream of random
values. 

"""
import sys
import pyacq as pq
import pyqtgraph as pg
import ephyviewer
import neurotic
import pdb, re
from pyRippleViewer import runProfiler
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

showEphySpikes = False
showScope = False
showTFR = False
showEphyTraceViewer = True
showEphyFrequencyViewer = True
showEphyAnnotator = False
signalTypesToPlot = ['hifreq']

# Start Qt application
app = pg.mkQApp()

# In host/process/thread 2: (you must communicate rpc_addr manually)
client = pyacq.RPCClient.get_client(rpc_addr)

# Get a proxy to published object; use this (almost) exactly as you
# would a local object:
dev = client['nip0']

if showScope:
    # Create a remote oscilloscope node to view the Ripple stream
    # nodegroup_osc = man.create_nodegroup()
    # osc = nodegroup_osc.create_node('QOscilloscope', name='scope0')
    #
    # Create a local scope
    osc = pyacq.QOscilloscope()
    #
    osc.configure(
        with_user_dialog=True, window_label='scope0', max_xsize=20.)
    osc.input.connect(dev.outputs['hifreq'])
    osc.initialize()
    osc.show()
    #
    osc.params['decimation_method'] = 'min_max'
    osc.params['mode'] = 'scroll'
    osc.params['display_labels'] = True
    osc.params['show_bottom_axis'] = True
    osc.params['show_left_axis'] = True
else:
    osc = None

if showTFR:
    ##  # spawn workers do calculate the spectrogram
    ##  tfr_workers = [man.create_nodegroup() for i in range(16)]
    ##  # Create a time frequency viewer
    ##  nodegroup_tfr = man.create_nodegroup()
    ##  tfr = nodegroup_tfr.create_node('QTimeFreq', name='tfr0')
    #
    # Create a local time frequency viewer
    tfr = pyacq.QTimeFreq()
    #
    tfr.configure(
        with_user_dialog=True, window_label='tfr0',
        max_xsize=20., nodegroup_friends=tfr_workers)
    tfr.input.connect(dev.outputs['hifreq'])
    tfr.initialize()
    tfr.show()
    #
    tfr.params['xsize'] = 1.
    tfr.params['nb_column'] = 8
    tfr.params['refresh_interval'] = 100
    tfr.params['show_axis'] = True
else:
    tfr = None

ephy_scope_list = []
if showEphyTraceViewer:
    # Create a remote ephyviewer TraceViewer node to view the Ripple stream
    # TODO: can't have local mainviewer with remote viewers
    # nodegroup_trace_viewer = man.create_nodegroup()
    # ephy_scope = nodegroup_trace_viewer.create_node('TraceViewerNode', name='pyacq_viewer')
    #
    # Create a local ephyviewer TraceViewer...
    for idx, signalTypeToPlot in enumerate(signalTypesToPlot):
        ephy_scope = pyacq.TraceViewerNode(
            name='traceviewer_{}'.format(signalTypeToPlot),
            useOpenGL=True, controls_parent=(idx == 0))
        #
        ephy_scope.configure(
            with_user_dialog=True, max_xsize=120.)
        ephy_scope.input.connect(dev.outputs[signalTypeToPlot])
        ephy_scope.initialize()
        #
        ephy_scope.show()
        ephy_scope_list.append(ephy_scope)

ephy_tfr_list = []
if showEphyFrequencyViewer and showEphyTraceViewer:
    for idx, signalTypeToPlot in enumerate(signalTypesToPlot):
        # TimeFreqViewer
        ephy_tfr = ephyviewer.TimeFreqViewer(
            source=ephy_scope_list[idx].source,
            useOpenGL=True,
            name='timefreq_{}'.format(signalTypeToPlot))
        ephy_tfr.show()
        ephy_tfr_list.append(ephy_tfr)
else:
    ephy_tfr = None


# Create a monitor node
mon = pyacq.StreamMonitor()
mon.configure()
mon.input.connect(dev.outputs['stim'])
mon.initialize()
if showEphySpikes:
    stimSpikeSource = pyacq.InputStreamEventAndEpochSource(mon.input)
    ephy_spk_viewer = ephyviewer.SpikeTrainViewer(
        name='stim_spikes', source=stimSpikeSource)

if showEphyAnnotator:
    epochAnnotatorSource = neurotic.NeuroticWritableEpochSource(
        filename='./test_annotations.csv', possible_labels=['label1', 'another_label'],
        color_labels=None, channel_name='', backup=True)
    # 
    # epochAnnotatorSource = ephyviewer.CsvEpochSource(
    #     filename='./test_annotations.csv', possible_labels=['label1', 'another_label'],
    #     color_labels=None, channel_name='')
    epochAnnotator = ephyviewer.EpochEncoder(source=epochAnnotatorSource, name='epoch')

#Create the main window that can contain several viewers
ephyWin = ephyviewer.MainViewer(
    debug=False, show_auto_scale=True,
    navigationToolBarClass=ephyviewer.PyAcqNavigationToolBar
    )
ephyWin.show()
#
tabifyWith = None
for ephy_view in ephy_scope_list:
    ephyWin.add_view(ephy_view, tabify_with=tabifyWith)
    if tabifyWith is None:
        tabifyWith = ephy_view.name

tabifyWith=None
for ephy_view in ephy_tfr_list:
    ephyWin.add_view(ephy_view, tabify_with=tabifyWith)
    if tabifyWith is None:
        tabifyWith = ephy_view.name

if showEphyAnnotator:
    ephyWin.add_view(epochAnnotator)

if showEphySpikes:
    ephyWin.add_view(ephy_spk_viewer)

# start nodes
for node in [osc, tfr, mon] + ephy_scope_list:
    if node is not None:
        node.start()

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
        pg.exec()
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