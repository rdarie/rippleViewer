# -*- coding: utf-8 -*-
# Copyright (c) 2016, French National Center for Scientific Research (CNRS)
# Distributed under the (new) BSD License. See LICENSE for more info.
"""
Noise generator node

Simple example of a custom Node class that generates a stream of random
values. 

"""
import sys
from pyacq.core import create_manager
from pyqtgraph.Qt import QtCore, QtGui
from pyacq.devices import XipppyBuffer
from pyacq.devices.ripple import ripple_analogsignal_types, randomSineGenerator
from pyacq.viewers import (
    QTimeFreq, QOscilloscope, TraceViewer,
    InputStreamAnalogSignalSource)
import ephyviewer
from neurotic import NeuroticWritableEpochSource

import numpy as np
import pdb
import pyacq
#
showScope = False
showTFR = False
showEphyTraceViewer = True
showEphyFrequencyViewer = True
signalTypeToPlot = 'hi-res'
dummyKWArgs = {
    'hifreq_fun': randomSineGenerator(
        centerFreq=20, dt=7500, noiseStd=0.25, sineAmp=1.)
    }

# Start Qt application
app = ephyviewer.mkQApp()


# Create a manager to spawn worker process to record and process audio
man = create_manager()
#
# nodegroup_dev = man.create_nodegroup()
# dev = nodegroup_dev.create_node(
#     'XipppyBuffer', name='nip0', dummy=True, dummy_kwargs=dummyKWArgs)
dev = XipppyBuffer(name='nip0', dummy=True, dummy_kwargs=dummyKWArgs)
#
requestedChannels = {
    signalTypeToPlot: [2, 3, 8]
    }
dev.configure(
    sample_interval_sec=50e-3, sample_chunksize_sec=20e-3,
    channels=requestedChannels, verbose=False, debugging=False)
for signalType in ripple_analogsignal_types:
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

if showEphyTraceViewer:
    # Create a remote ephyviewer TraceViewer node to view the Ripple stream
    # TODO: can't have local mainviewer with remote viewers
    # nodegroup_trace_viewer = man.create_nodegroup()
    # ephy_scope = nodegroup_trace_viewer.create_node('TraceViewer', name='pyacq_viewer')
    #
    # Create a local ephyviewer TraceViewer...
    ephy_scope = TraceViewer(name='ephy_viewer_{}'.format(signalTypeToPlot))
    #
    ephy_scope.configure(
        with_user_dialog=True, window_label='ephy_scope_{}'.format(signalTypeToPlot), max_xsize=20.)
    ephy_scope.input.connect(dev.outputs[signalTypeToPlot])
    ephy_scope.initialize()
    ephy_scope.show()
else:
    ephy_scope = None

if showEphyFrequencyViewer and showEphyTraceViewer:
    ephy_tfr = ephyviewer.TimeFreqViewer(
        source=ephy_scope.source, name='timefreq_{}'.format(signalTypeToPlot))
    ephy_tfr.show()
else:
    ephy_tfr = None

epochAnnotatorSource = NeuroticWritableEpochSource(
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
#
for ephy_view in [ephy_scope, ephy_tfr]:
    if ephy_view is not None:
        ephyWin.add_view(ephy_view)
ephyWin.add_view(epochAnnotator)
ephyWin.show()

# start nodes
for node in [dev, osc, tfr, ephy_scope]:
    if node is not None:
        node.start()

if __name__ == '__main__':
    if sys.flags.interactive == 0:
        pg.exec()