import psutil
import time
import os, sys
import numpy as np
import pandas as pd
import collections
import line_profiler
import pdb

from PyQt5.QtCore import pyqtRemoveInputHook, pyqtRestoreInputHook
from inspect import getmembers, isfunction, isclass

psutil_process = psutil.Process(os.getpid())
startTime = 0

def memory_usage_psutil():
    # return the memory usage in MB
    process = psutil.Process(os.getpid())
    mem = process.memory_info()[0] / float(2 ** 20)
    return mem

def get_memory_usage():
    # return the memory usage in MB
    # if 'psutil_process' in globals():
    #     psutil_process = globals()['psutil_process']
    # else:
    #     psutil_process = psutil.Process(os.getpid())
    #     globals().update({'psutil_process': psutil_process})
    # 
    global psutil_process
    mem = psutil_process.memory_info()[0] / float(2 ** 20)
    return mem

def print_memory_usage(
        prefix='profiling', placeholder=None):
    if placeholder is None:
        placeholder = ': using {:.1f} MB'
    mem = get_memory_usage()
    print(prefix + placeholder.format(mem))
    return

def start_timing(
        mess='Starting timer...'):
    global startTime
    startTime = time.perf_counter()
    return

def stop_timing(
        prefix='profiling', placeholder=None):
    if placeholder is None:
        placeholder = ': took {:.1f} sec'
    global startTime
    endTime = time.perf_counter()
    print(prefix + placeholder.format(endTime - startTime))
    return

def register_module_with_profiler(
        mod, profile, verbose=False):
    functionList = [o[1] for o in getmembers(mod) if isfunction(o[1])]
    #
    for thisFun in functionList:
        if verbose:
            print('Adding function {} to line_profiler from {}'.format(thisFun.__name__, mod.__name__))
        profile.add_function(thisFun)
    #
    classList = [o[1] for o in getmembers(mod) if isclass(o[1])]
    for thisClass in classList:
        functionListThisClass = [o[1] for o in getmembers(thisClass) if isfunction(o[1])]
        for thisClassFun in functionListThisClass:
            if verbose:
                print('Adding function {} to line_profiler from {}.{}'.format(thisClassFun.__name__, mod.__name__, thisClass.__name__))
            profile.add_function(thisClassFun)
    return

def register_list_with_profiler(
        functionList, profile):
    for thisFun in functionList:
        if isfunction(thisFun):
            profile.add_function(thisFun)
    return

#  hack original line_profiler.show_text to override dict order
def show_profiler_text(
        stats, unit, output_unit=None,
        stream=None, stripzeros=False, minimum_time=None):
    """ Show text for the given timings.
    """
    if stream is None:
        stream = sys.stdout
    #
    stream.write('Time spent per function:\n')
    total_timings = {}
    for (fn, lineno, name), timings in stats.items():
        total_time = np.sum([tim[2] for tim in timings]) * unit # in seconds
        total_timings[(fn, lineno, name)] = total_time
    #
    total_timing_srs = pd.Series(total_timings)
    total_timing_srs.name = 'total time (sec)'
    total_timing_srs.index.names = ['fn', 'lineno', 'name']
    total_timing_df = total_timing_srs.reset_index()
    # total_timing_df.loc[:, 'fn'] = total_timing_df['fn'].apply(lambda x: x.split(os.path.sep)[-1])
    total_timing_df.loc[:, 'total time (sec)'] = total_timing_df['total time (sec)'].apply(lambda x: '{:g}'.format(x))
    stream.write(total_timing_df.to_string())
    stream.write('\n\n')
    if output_unit is not None:
        stream.write('Timer units: %g sec\n' % output_unit)
    else:
        stream.write('Timer units: %g sec\n' % unit)
    #
    for (fn, lineno, name), timings in stats.items():
        # timings is stats[fn, lineno, name]
        if minimum_time is not None:
            if total_timings[(fn, lineno, name)] < minimum_time:
                continue
        line_profiler.show_func(
            fn, lineno, name, timings, unit,
            output_unit=output_unit, stream=stream, stripzeros=stripzeros)
    return

def orderLStatsByTime(
        statsPackage=None, scriptName=None, ascending=False):
    if statsPackage is None:
        statsPackage = line_profiler.load_stats(scriptName)
    stats = {k: v for k, v in statsPackage.timings.items() if len(v)}
    unit = statsPackage.unit
    allKeys = []
    totalTimes = []
    for (fn, lineno, name), timings in stats.items():
        total_time = 0.0
        for inner_lineno, nhits, thisTime in timings:
            total_time += thisTime
        allKeys.append((fn, lineno, name))
        totalTimes.append(total_time)
    orderedIdx = np.argsort(totalTimes)
    if not ascending:
        orderedIdx = orderedIdx[::-1]
    orderedStats = collections.OrderedDict()
    for i in orderedIdx:
        orderedStats[allKeys[i]] = stats[allKeys[i]]
    return orderedStats, unit

def profileFunction(
        topFun=None, modulesToProfile=None,
        registerTopFun=True,
        outputBaseFolder='.',
        namePrefix=None, nameSuffix=None,
        outputUnits=None, minimum_time=None, verbose=False,
        saveTextOnly=False):
    # outputUnits is of type float, e.g. 10^-6 seconds
    if not os.path.exists(outputBaseFolder):
        os.makedirs(outputBaseFolder, exist_ok=True)
    profile = line_profiler.LineProfiler()
    for mod in modulesToProfile:
        register_module_with_profiler(
            mod, profile, verbose=verbose)
    if registerTopFun:
        profile.add_function(topFun)
    #
    profile.runcall(topFun)
    #
    if namePrefix is not None:
        fileName = namePrefix
    else:
        fileName = ''
    if nameSuffix is not None:
        fileName = fileName + '_' + nameSuffix
    if not saveTextOnly:
        outfile = os.path.join(
            outputBaseFolder,
            '{}.lprof'.format(fileName))
        profile.dump_stats(outfile)
    orderedStats, unit = orderLStatsByTime(
        statsPackage=profile.get_stats())
    #
    outfiletext = os.path.join(
        outputBaseFolder,
        '{}.txt'.format(fileName))
    with open(outfiletext, 'w') as f:
        show_profiler_text(
            orderedStats, unit,
            output_unit=outputUnits, stream=f, minimum_time=minimum_time)
    return

def debugTrace():
    pyqtRemoveInputHook()
    try:
        debugger = pdb.Pdb()
        debugger.reset()
        debugger.do_next(None)
        user_frame = sys._getframe().f_back
        debugger.interaction(user_frame, None)
    finally:
        pyqtRestoreInputHook()