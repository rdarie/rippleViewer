# -*- coding: utf-8 -*-
# Copyright (c) 2016, French National Center for Scientific Research (CNRS)
# Distributed under the (new) BSD License. See LICENSE for more info.
"""
Noise generator node

Simple example of a custom Node class that generates a stream of random
values. 

"""
# import numpy as np
from http import server
import subprocess, os
import pdb
from pyacq.core import create_manager, rpc
from pyqtgraph.Qt import QtCore, QtGui
import pyqtgraph as pg
import pyacq
from pyacq.devices import XipppyBuffer
from pyacq.devices.ripple import ripple_signal_types
from pyacq.viewers import QTimeFreq, QOscilloscope
import xipppy as xp

showScope = True
showTFR = True
# just in case
xp._close()

# Start Qt application
app = QtGui.QApplication([])

# Create a manager to spawn worker process to record and process audio
man = create_manager()
#
nodegroup = man.create_nodegroup()
dev = nodegroup.create_node('XipppyBuffer', name='nip0')
requestedChannels = {
    'hi-res': [2,3,8]
    }
dev.configure(
    sample_interval_sec=.2, sample_chunksize_sec=.1,
    channels=requestedChannels, verbose=False, debugging=False)
for signalType in ripple_signal_types:
    dev.outputs[signalType].configure(
        protocol='tcp', transfermode='sharedmem'
        # protocol='tcp', interface='127.0.0.1', transfermode='plaindata'
        )
dev.initialize()

if showScope:
    # Create a remote oscilloscope node to view the Ripple stream
    # osc = nodegroup.create_node('QOscilloscope', name='scope0')
    #
    osc = QOscilloscope()
    osc.configure(with_user_dialog=True, max_xsize=20.)
    osc.input.connect(dev.outputs['hi-res'])
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
    tfr_workers = [man.create_nodegroup() for i in range(8)]
    # Create a time frequency viewer
    tfr = nodegroup.create_node('QTimeFreq', name='tfr0')
    tfr.configure(with_user_dialog=True, nodegroup_friends=tfr_workers)
    tfr.input.connect(dev.outputs['hi-res'])
    tfr.initialize()
    tfr.show()
    #
    tfr.params['xsize'] = 1.
    tfr.params['nb_column'] = 8
    tfr.params['refresh_interval'] = 100
    tfr.params['show_axis'] = True
else:
    tfr = None

# start nodes
for node in [dev, osc, tfr]:
    if node is not None:
        node.start()

if __name__ == '__main__':
    import sys
    if sys.flags.interactive == 0:
        app.exec_()