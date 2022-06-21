# -*- coding: utf-8 -*-
# Copyright (c) 2016, French National Center for Scientific Research (CNRS)
# Distributed under the (new) BSD License. See LICENSE for more info.
"""
Noise generator node

Simple example of a custom Node class that generates a stream of random
values. 

"""
import sys
import pandas as pd
from pyacq.core import create_manager
from pyqtgraph.Qt import QtCore, QtGui
from pyacq.devices import XipppyBuffer
from pyacq.devices.ripple import ripple_analogsignal_types
from pyacq.viewers import QTimeFreq, QOscilloscope, TraceViewer, InputStreamAnalogSignalSource
import ephyviewer
from neurotic import NeuroticWritableEpochSource

import numpy as np
import pdb
import pyacq
#
showScope = False
showTFR = False
signalTypeToPlot = 'hifreq'

# Start Qt application
app = ephyviewer.mkQApp()

# Create a manager to spawn worker process to record and process audio
man = create_manager()
#
nodegroup_dev = man.create_nodegroup()
dev = nodegroup_dev.create_node('XipppyBuffer', name='nip0', dummy=True)
# dev = XipppyBuffer(name='nip0', dummy=True)
#
requestedChannels = {
    signalTypeToPlot: [2, 3, 8]
    }
dev.configure(
    sample_interval_sec=50e-3, sample_chunksize_sec=20e-3,
    channels=requestedChannels, verbose=False, debugging=False)
for signalType in ripple_analogsignal_types:
    dev.outputs[signalType].configure(
        # protocol='tcp', transfermode='sharedmem', double=True
        protocol='tcp', interface='127.0.0.1', transfermode='plaindata'
        )
dev.initialize()

if showScope:
    # Create a remote oscilloscope node to view the Ripple stream
    # nodegroup_osc = man.create_nodegroup()
    # osc = nodegroup_osc.create_node('QOscilloscope', name='scope0')
    #
    # Create a local scope
    osc = QOscilloscope()
    #
    osc.configure(
        with_user_dialog=True, window_label='scope0', max_xsize=20.)
    osc.input.connect(dev.outputs[signalTypeToPlot])
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
    # spawn workers do calculate the spectrogram
    tfr_workers = [man.create_nodegroup() for i in range(16)]
    # Create a time frequency viewer
    nodegroup_tfr = man.create_nodegroup()
    tfr = nodegroup_tfr.create_node('QTimeFreq', name='tfr0')
    #
    # Create a local time frequency viewer
    # tfr = QTimeFreq()
    #
    tfr.configure(
        with_user_dialog=True, window_label='tfr0',
        max_xsize=20., nodegroup_friends=tfr_workers)
    tfr.input.connect(dev.outputs[signalTypeToPlot])
    tfr.initialize()
    tfr.show()
    #
    tfr.params['xsize'] = 1.
    tfr.params['nb_column'] = 8
    tfr.params['refresh_interval'] = 100
    tfr.params['show_axis'] = True
else:
    tfr = None

#signals
sigs = np.random.rand(100000,16)
sample_rate = 1000.
t_start = 0.
#Create a datasource for the viewer
# here we use InMemoryAnalogSignalSource but
# you can alose use your custum datasource by inheritance
source = ephyviewer.InMemoryAnalogSignalSource(sigs, sample_rate, t_start)
#create a viewer for signal with TraceViewer
# TraceViewer normally accept a AnalogSignalSource but
# TraceViewer.from_numpy is facitilty function to bypass that
ephy_trace_viewer = ephyviewer.TraceViewer(source=source, name='ephy_viewer')
#
# Create a remote ephyviewer TraceViewer node to view the Ripple stream
# TODO: can't have local mainviewer with remote viewers
# nodegroup_trace_viewer = man.create_nodegroup()
# pyacq_trace_viewer = nodegroup_trace_viewer.create_node('TraceViewer', name='pyacq_viewer')
#
# Create a local ephyviewer TraceViewer...
pyacq_trace_viewer = pyacq.viewers.TraceViewer(name='pyacq_viewer')
#
pyacq_trace_viewer.configure(
    with_user_dialog=True, window_label='pyacq_scope0', max_xsize=120.)
pyacq_trace_viewer.input.connect(dev.outputs[signalTypeToPlot])
pyacq_trace_viewer.initialize()
pyacq_trace_viewer.show()

epochAnnotatorSource = NeuroticWritableEpochSource(
    filename='./test_annotations.csv', possible_labels=['label1', 'another_label'],
    color_labels=None, channel_name='', backup=True)
# 
# epochAnnotatorSource = ephyviewer.CsvEpochSource(
#     filename='./test_annotations.csv', possible_labels=['label1', 'another_label'],
#     color_labels=None, channel_name='')

epochAnnotator = ephyviewer.EpochEncoder(source=epochAnnotatorSource)
#Create the main window that can contain several viewers
ephyWin = ephyviewer.MainViewer(
    debug=False, show_auto_scale=True,
    navigationToolBarClass=ephyviewer.PyAcqNavigationToolBar
    )

ephyWin.add_view(ephy_trace_viewer)
ephyWin.add_view(pyacq_trace_viewer)
ephyWin.add_view(epochAnnotator)
ephyWin.show()

pyacq_trace_viewer.start()
# start nodes
for node in [dev, osc, tfr]:
    if node is not None:
        node.start()

if __name__ == '__main__':
    propsList = {
        'QtGui.QWidget': sorted(dir(QtGui.QWidget)),
        'ephyTraceViewer': sorted(dir(ephy_trace_viewer)),
        'pyacqTraceViewer': sorted(dir(pyacq_trace_viewer)),
        'QOscilloscope': sorted(dir(osc))
        }

    allProps = np.setdiff1d(
        np.union1d(
            np.union1d(propsList['ephyTraceViewer'], propsList['pyacqTraceViewer']), propsList['QOscilloscope']),
        propsList['QtGui.QWidget'])
    propsPresent = pd.DataFrame({
        key: [(propName in propsList[key]) for propName in allProps]
        for key in ['pyacqTraceViewer', 'ephyTraceViewer', 'QOscilloscope']
        }, index=allProps)

    def color_boolean(val):
        color =''
        if val == True:
            color = 'green'
        elif val == False:
            color = 'red'
        return 'background-color: {}'.format(color)
    propsPresent.style.applymap(color_boolean).to_html('viewer_props.html')

    if sys.flags.interactive == 0:
        app.exec_()