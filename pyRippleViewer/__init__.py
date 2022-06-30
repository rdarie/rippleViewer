
import sys
if sys.platform == 'win32':
    import ctypes
    winmm = ctypes.WinDLL('winmm')
    winmm.timeBeginPeriod(1)

import pyqtgraph
# pyqtgraphOpts = dict(useOpenGL=True, enableExperimental=True, useNumba=True)
pyqtgraphOpts = dict(useOpenGL=True, enableExperimental=True, useNumba=True)
pyqtgraph.setConfigOptions(**pyqtgraphOpts)

# don't limit frame rate to vsync
sfmt = pyqtgraph.Qt.QtGui.QSurfaceFormat()
sfmt.setSwapInterval(0)
pyqtgraph.Qt.QtGui.QSurfaceFormat.setDefaultFormat(sfmt)

import ephyviewer

import pyacq
