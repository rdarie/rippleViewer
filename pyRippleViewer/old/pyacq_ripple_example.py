# -*- coding: utf-8 -*-
# Copyright (c) 2016, French National Center for Scientific Research (CNRS)
# Distributed under the (new) BSD License. See LICENSE for more info.
"""
Noise generator node

Simple example of a custom Node class that generates a stream of random
values. 

"""
import numpy as np
import pdb
from pyacq.core import create_manager
from pyqtgraph.Qt import QtCore, QtGui
from pyacq.devices import XipppyBuffer
import pyqtgraph as pg
from pyacq.viewers import QOscilloscope
import xipppy as xp

if __name__ == '__main__':
    import sys
    if sys.flags.interactive == 0:
        # Start Qt application
        app = pg.mkQApp()
        # just in case
        xp._close()
        # Create a xippy node
        dev = XipppyBuffer()
        dev.configure(
            sample_interval_sec=.5, sample_chunksize_sec=.5,
            channels={}, verbose=False, debugging=False)
        for signalName in dev.signalTypes:
            dev.outputs[signalName].configure(
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

        pg.exec()