import psutil
import time
import os, sys
import numpy as np
import pandas as pd
import collections
import line_profiler
import pdb
import dill as pickle
import yappi

from inspect import getmembers, isfunction, isclass

psutil_process = psutil.Process(os.getpid())
startTime = 0


yappiNameExplanations = {
    'name': 'name of the executed function',
    'module': 'module name of the executed function',
    'lineno': 'line number of the executed function',
    'ncall': 'number of times the executed function is called.',
    'nactualcall': 'number of times the executed function is called, excluding the recursive calls.',
    'builtin': 'bool, indicating whether the executed function is a builtin',
    'ttot': 'total time spent in the executed function (ttot)',
    'tsub': 'total time spent in the executed function, excluding subcalls (tsub)',
    'tavg': 'per-call average total time spent in the executed function (tavg)',
    'index': 'unique id for the YFuncStat object',
    'children': 'list of YChildFuncStat objects',
    'ctx_id': 'id of the underlying context (thread)',
    'ctx_name': 'name of the underlying context (thread)',
    'full_name': 'unique full name of the executed function',
    }

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


def processYappiResults(
        fileName=None, folder=None,
        minimum_time=None, modulesToPrint=[],
        run_time=0., metadata={}
        ):
    attributesToPrint = [
        'ctx_id', 'ctx_name', 'name', 'lineno',
        'ncall', 'ttot', 'tsub', 'tavg', 'module']
    clockType = yappi.get_clock_type()
    fileName = fileName + '_{}_time'.format(clockType)
    ##
    if not os.path.exists(folder):
        os.makedirs(folder, exist_ok=True)
    profilerResultsPath = os.path.join(
        folder, fileName)
    yStats = yappi.get_func_stats()
    #
    # pdb.set_trace()
    yStats.save(profilerResultsPath + '.pstat', type="pstat")
    callGrindResultsPath = os.path.join(folder, f'callgrind.{fileName}')
    yStats.save(callGrindResultsPath, type="callgrind")
    #
    if len(modulesToPrint):
        keepList = [os.path.dirname(mod.__path__[0]) for mod in modulesToPrint]
        filter_fun = lambda x: any([(searchTerm in x.module) for searchTerm in keepList])
        statsSelected = yappi.get_func_stats(filter_callback=filter_fun)
        statsSelected.save(profilerResultsPath + '_selected.pstat', type="pstat")
        callGrindResultsPath = os.path.join(folder, f'callgrind.{fileName}_selected')
        statsSelected.save(callGrindResultsPath, type="callgrind")
    yStatsDict = {
            attrName: []
            for attrName in attributesToPrint
            }
    for ySt in yStats:
        if ySt is not None:
            if minimum_time is not None:
                if ySt.ttot < minimum_time:
                    continue
            for attrName in attributesToPrint:
                yStatsDict[attrName].append(ySt.__getattribute__(attrName))
    yStatsDF = pd.DataFrame(yStatsDict)
    yStatsDF.sort_values(['ctx_id', 'ttot'], ascending=[True, False], inplace=True)
    if len(modulesToPrint):
        mask = pd.concat([yStatsDF['module'].apply(
            lambda x: modPath in x) for modPath in keepList], axis='columns').any(axis='columns')
        yStatsDF = yStatsDF.loc[mask, :]
    runCaption = "Run lasted {:g} sec. ({} time)".format(run_time, clockType)
    style = (
        yStatsDF.rename(columns=yappiNameExplanations).style
            .set_caption(runCaption)
            .background_gradient(axis=0, subset=yappiNameExplanations['ttot'])
            .background_gradient(axis=0, subset=yappiNameExplanations['tavg'], cmap="YlOrBr")
            .set_sticky(axis="columns")
            .hide(axis='index')
            .set_table_styles([
                {"selector": "", "props": [("border", "1px solid grey")]},
                {"selector": "tbody td", "props": [("border", "1px solid grey")]},
                {"selector": "th", "props": [("border", "1px solid grey")]}
                ]))
    style.to_html(profilerResultsPath + '.html')
    with open(profilerResultsPath + '_run_metadata.pickle', 'wb') as handle:
        pickle.dump(metadata, handle)
    #
    threads = yappi.get_thread_stats()
    for thread in threads:
        try:
            yStatsThisThread = yappi.get_func_stats(ctx_id=thread.id)
            threadName = thread.name.replace('/', '').replace("\\", '')
            # visualize .pstat results with snakeviz
            # https://jiffyclub.github.io/snakeviz/
            yStatsThisThread.save(profilerResultsPath + '_thread_{}_{}.pstat'.format(
                thread.id, threadName), type='pstat')
            # visualize .callgrind results with kcachegrindwin on linux
            # Or, on windows, qcachegrindwin, available precompiled at
            # https://sourceforge.net/projects/qcachegrindwin/
            callGrindResultsThisThreadPath = os.path.join(
                folder, f'callgrind.{fileName}_thread_{thread.id}_{threadName}')
            yStatsThisThread.save(callGrindResultsThisThreadPath, type='callgrind')
            if len(modulesToPrint):
                statsSelected = yappi.get_func_stats(ctx_id=thread.id, filter_callback=filter_fun)
                statsSelected.save(profilerResultsPath + '_thread_{}_{}_selected.pstat'.format(
                    thread.id, threadName), type='pstat')
                callGrindResultsThisThreadPath = os.path.join(
                    folder, f'callgrind.{fileName}_thread_{thread.id}_{threadName}_selected')
                statsSelected.save(callGrindResultsThisThreadPath, type="callgrind")
        except:
            continue
            