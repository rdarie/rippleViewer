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
import ephyviewer
import neurotic
import pdb
#
showScope = False
showTFR = False
showEphyTraceViewer = True
showEphyFrequencyViewer = True
showEphyAnnotator = False

dummyKWArgs = {
    'hires_fun': pq.randomSineGenerator(
        centerFreq=20, sr=2000, noiseStd=0.05, sineAmp=1.),
    # 'hifreq_fun': pq.randomSineGenerator(
    #     centerFreq=40, dt=15000, noiseStd=0.05, sineAmp=1.),
    'hifreq_fun': pq.randomChirpGenerator(
        startFreq=10, stopFreq=40, freqPeriod=2.,
        sr=15000, noiseStd=0.05, sineAmp=1.),
    'signal_type_lookup': {'hifreq': [eNum for eNum in range(1, 129)]}
    }

'''fun = dummyKWArgs['hifreq_fun']
hifreq_data, timestamp = dummyKWArgs['hifreq_fun'](npoints=20000, elecs=[1,2,3], start_timestamp=3.5e4)
hires_data, timestamp = dummyKWArgs['hires_fun'](npoints=20000, elecs=[1,2,3], start_timestamp=3.5e4)
from matplotlib import pyplot as plt
plt.plot(hires_data.reshape((20000, 3), order='F')); plt.show()'''

# Start Qt application
app = ephyviewer.mkQApp()

# Create a manager to spawn worker process to record and process audio
# man = pq.create_manager()
#
# nodegroup_dev = man.create_nodegroup()
# dev = nodegroup_dev.create_node(
#     'XipppyBuffer', name='nip0')
dev = pq.XipppyBuffer(
    name='nip0', dummy=True,
    dummy_kwargs=dummyKWArgs)
#
requestedChannels = {
    # 'hi-res': [2, 3, 8],
    # 'hifreq': [2, 3, 12]
    }
signalTypesToPlot = ['hifreq', 'hi-res']

dev.configure(
    sample_interval_sec=50e-3, sample_chunksize_sec=50e-3,
    channels=requestedChannels, verbose=False, debugging=False)
for signalType in pq.ripple_analogsignal_types:
    dev.outputs[signalType].configure(
        protocol='tcp', transfermode='sharedmem', double=True
        # protocol='tcp', interface='127.0.0.1', transfermode='plaindata'
        )
dev.initialize()

if showScope:
    # Create a remote oscilloscope node to view the Ripple stream
    # nodegroup_osc = man.create_nodegroup()
    # osc = nodegroup_osc.create_node('QOscilloscope', name='scope0')
    #
    # Create a local scope
    osc = pq.QOscilloscope()
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
    tfr = pq.QTimeFreq()
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
        ephy_scope = pq.TraceViewerNode(
            name='traceviewer_{}'.format(signalTypeToPlot),
            controlsParentViewer=(idx == 0))
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
        ephy_tfr = ephyviewer.TimeFreqViewer(
            source=ephy_scope_list[idx].source,
            name='timefreq_{}'.format(signalTypeToPlot))
        ephy_tfr.show()
        ephy_tfr_list.append(ephy_tfr)
else:
    ephy_tfr = None

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


# start nodes
for node in [dev, osc, tfr] + ephy_scope_list:
    if node is not None:
        node.start()

runProfiler = True
if __name__ == '__main__':
    if sys.flags.interactive == 0:
        if runProfiler:
            import yappi, time
            from pyRippleViewer.profiling import profiling as prf
            yappiClockType = "cpu"
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
            from datetime import datetime as dt
            import os
            now = dt.now()
            dateStr = now.strftime('%Y%m%d')
            timeStr = now.strftime('%H%M')
            profilerResultsFileName = '{}_{}_pid_{}'.format(
                __file__.split('.')[0], timeStr, os.getpid())
            profilerResultsFolder = '../yappi_profiler_outputs/{}'.format(dateStr)
            ###
            minimum_time = 1e-1
            modulesToPrint = []  # [pq, ephyviewer]
            runMetadata = {}
            ###
            
            prf.processYappiResults(
                fileName=profilerResultsFileName, folder=profilerResultsFolder,
                minimum_time=minimum_time, modulesToPrint=modulesToPrint,
                run_time=run_time, metadata=runMetadata)