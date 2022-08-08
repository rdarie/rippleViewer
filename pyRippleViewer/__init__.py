
import sys
import PySide6
import pyqtgraph as pg
import ephyviewer as ephy
from ephyviewer.myqt import QT, QT_LIB
import pyacq

from .tridesclous import *

if sys.platform == 'win32':
    import ctypes
    winmm = ctypes.WinDLL('winmm')
    winmm.timeBeginPeriod(1)

# pyqtgraphOpts = dict(useOpenGL=True, enableExperimental=True, useNumba=True)
pyqtgraphOpts = dict(useOpenGL=True, enableExperimental=True, useNumba=True)
pg.setConfigOptions(**pyqtgraphOpts)

# don't limit frame rate to vsync
sfmt = QT.QSurfaceFormat()
sfmt.setSwapInterval(0)
QT.QSurfaceFormat.setDefaultFormat(sfmt)

from .profiling_opts import *
yappiModulesToPrint = [pyacq, ephy, pg]  # [pq, ephy, pg]