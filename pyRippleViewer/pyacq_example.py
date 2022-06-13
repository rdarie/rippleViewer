# -*- coding: utf-8 -*-
# Copyright (c) 2016, French National Center for Scientific Research (CNRS)
# Distributed under the (new) BSD License. See LICENSE for more info.
"""
Noise generator node

Simple example of a custom Node class that generates a stream of random
values. 

"""
import numpy as np

from pyacq.core import create_manager
from pyqtgraph.Qt import QtCore, QtGui
from pyacq.devices import NumpyDeviceBuffer
import pyqtgraph as pg
from pyacq.viewers import QOscilloscope, QTimeFreq

# Start Qt application
app = pg.mkQApp()
# Create a manager to spawn worker process to record and process audio
man = create_manager()

# Create a noise generator node
dev = NumpyDeviceBuffer()
dev.configure(nb_channel=32, chunksize=256, sample_interval=3e4 ** -1)
dev.output.configure(
    protocol='tcp', interface='127.0.0.1', transfermode='plaindata')
dev.initialize()

# Create an oscilloscope node to view the noise stream
osc = QOscilloscope()
osc.configure(with_user_dialog=True)
osc.input.connect(dev.output)
osc.initialize()
osc.show()

# spawn workers do calculate the spectrogram
tfr_workers = [man.create_nodegroup() for i in range(12)]
# Create a time frequency viewer
tfr = QTimeFreq()
tfr.configure(with_user_dialog=True, nodegroup_friends=tfr_workers)
tfr.input.connect(dev.output)
tfr.initialize()
tfr.show()

tfr.params['xsize'] = 1.
tfr.params['nb_column'] = 8
tfr.params['refresh_interval'] = 100

# start nodes
osc.start()
dev.start()
tfr.start()

if __name__ == '__main__':
    import sys
    if sys.flags.interactive == 0:
        app.exec_()