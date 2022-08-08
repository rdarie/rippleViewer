
import logging
import os
from pathlib import Path
import yappi
from datetime import datetime as dt

packageImportTime = dt.now()

runProfiler = False
LOGGING = True

logFormatDict = dict(
    format='L{levelno}: {asctime}{msecs: >5.1f}: {name: >30} thr. {thread: >12X}: thr. n. {threadName}: {message}',
    style='{', datefmt='%M:%S:',
    level=logging.INFO)

def startLogger(
        filePath, fileName):
    global packageImportTime
    pathHere = Path(filePath)
    thisFileName = pathHere.stem
    logFileDir = pathHere.resolve().parent.parent
    logFileName = os.path.join(
        logFileDir, 'logs',
        f"{thisFileName}_{packageImportTime.strftime('%Y_%m_%d_%M%S')}.log"
        )
    logging.basicConfig(
        filename=logFileName,
        **logFormatDict
        )
    logger = logging.getLogger(fileName)
    return logger

dateStr = packageImportTime.strftime('%Y%m%d')
timeStr = packageImportTime.strftime('%H%M')

yappiClockType = 'cpu'
yappi_minimum_time = 1e-2
yappi.set_clock_type(yappiClockType)

def getProfilerPath(filePath):
    pathHere = Path(filePath)
    thisFileName = pathHere.stem
    profilerResultsFileName = '{}_{}_pid_{}'.format(
        thisFileName, timeStr, os.getpid())
    logFileDir = pathHere.resolve().parent.parent
    profilerResultsFolder = os.path.join(
        logFileDir, 'yappi_profiler_outputs', f'{dateStr}')
    return profilerResultsFileName, profilerResultsFolder
