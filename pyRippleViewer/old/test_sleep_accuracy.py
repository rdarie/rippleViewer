# -*- coding: utf-8 -*-
# Copyright (c) 2016, French National Center for Scientific Research (CNRS)
# Distributed under the (new) BSD License. See LICENSE for more info.
"""
Noise generator node

Simple example of a custom Node class that generates a stream of random
values. 

"""
import sys
if sys.platform == 'win32':
    from time import sleep
    import timeit
    timeOverhead = (timeit.timeit('sleep(0.025)', number=100, globals=globals()) / 0.025 - 100)
    print('Before: time overhead was {:.2f}%'.format(timeOverhead))
    import ctypes
    winmm = ctypes.WinDLL('winmm')
    winmm.timeBeginPeriod(1)
    timeOverhead = (timeit.timeit('sleep(0.025)', number=100, globals=globals()) / 0.025 - 100)
    print('After: time overhead was {:.2f}%'.format(timeOverhead))
else:
    print('Timer selection only available on Windows!')