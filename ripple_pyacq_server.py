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
from pyacq.viewers import QOscilloscope
import xipppy as xp

# just in case
xp._close()

# Start Qt application
app = QtGui.QApplication([])
# create xipppy device node in remote process
dev_proc = rpc.ProcessSpawner()
dev = dev_proc.client._import('pyacq.devices.ripple').XipppyBuffer()
dev.configure(
    sample_interval_sec=1., channels={}, verbose=False, debugging=False)
for signalType in ripple_signal_types:
    dev.outputs[signalType].configure(
        protocol='tcp', interface='127.0.0.1', transfermode='plaindata')
dev.initialize()

# Create an oscilloscope node to view the Ripple stream
osc = QOscilloscope()
osc.configure(with_user_dialog=True)
osc.input.connect(dev.outputs['hi-res'])
osc.initialize()
osc.show()
osc.params['decimation_method'] = 'min_max'
osc.params['mode'] = 'scroll'
osc.params['display_labels'] = True
osc.params['show_bottom_axis'] = True
osc.params['show_left_axis'] = True

# start nodes
osc.start()
dev.start()

if __name__ == '__main__':
    import sys
    if sys.flags.interactive == 0:
        app.exec_()