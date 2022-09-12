import os, pdb
import time

from pyRippleViewer import *

if LOGGING:
    logger = startLogger(__file__, __name__)

import sys
import re


def main():
    requested_signal_types = ['markers', 'devices']
    # Start Qt application
    app = pg.mkQApp()
    #    
    viconClient = pyacq.Vicon(
        name='vicon', requested_signal_types=requested_signal_types)
    viconClient.configure()
    ####################################################
    # connect viconClient inputs
    ####################################################
    # configure viconClient outputs
    for outputName, output in viconClient.outputs.items():
        print(output.spec)
        output.configure(
            # protocol='tcp', interface='127.0.0.1', transfermode='sharedmem', double=True,
            protocol='inproc', transfermode='sharedmem', double=True,
            # protocol='inproc', transfermode='plaindata', double=True,
            )
    ####################################################
    viconClient.initialize()
    viconClient.start()
    ######################
    print(f'{__file__} starting qApp...')
    app.exec()
    ######################
    return

if __name__ == '__main__':
    if runProfiler:
        runMetadata = {}
        yappi.start()
        start_time = time.perf_counter()
    try:
        ###############
        main()
        ###############
    finally:
        if runProfiler:
            print('Saving yappi profiler outputs')
            yappi.stop()
            stop_time = time.perf_counter()
            run_time = stop_time - start_time
            profilerResultsFileName, profilerResultsFolder = getProfilerPath(__file__)
            #
            from pyRippleViewer.profiling import profiling as prf   
            prf.processYappiResults(
                fileName=profilerResultsFileName, folder=profilerResultsFolder,
                minimum_time=yappi_minimum_time, modulesToPrint=yappiModulesToPrint,
                run_time=run_time, metadata=runMetadata)