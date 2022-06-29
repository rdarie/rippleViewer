
import sys
if sys.platform == 'win32':
    import ctypes
    winmm = ctypes.WinDLL('winmm')
    winmm.timeBeginPeriod(1)

runProfiler = True
