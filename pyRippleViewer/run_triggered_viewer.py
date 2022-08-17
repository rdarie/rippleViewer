# -*- coding: utf-8 -*-
# Copyright (c) 2016, French National Center for Scientific Research (CNRS)
# Distributed under the (new) BSD License. See LICENSE for more info.
"""
Noise generator node

Simple example of a custom Node class that generates a stream of random
values. 

"""

from pyRippleViewer import *
import pdb
import sys, re, time

if LOGGING:
    logger = startLogger(__file__, __name__)

usage = """Usage:
    python pyacq_ripple_host.py [address]

# Examples:
python host_server.py
python host_server.py
"""

xipppy_rpc_addr = 'tcp://127.0.0.1:5001'
websockets_rpc_addr = 'tcp://127.0.0.2:5001'


def main():
    # Start Qt application
    app = pg.mkQApp()

    # In host/process/thread 2: (you must communicate rpc_addr manually)
    xipppy_client = pyacq.RPCClient.get_client(xipppy_rpc_addr)

    # Get a proxy to published object; use this (almost) exactly as you
    # would a local object:
    txBuffer = xipppy_client['nip0']

    # In host/process/thread 2: (you must communicate rpc_addr manually)
    websockets_client = pyacq.RPCClient.get_client(websockets_rpc_addr)

    # Get a proxy to published object; use this (almost) exactly as you
    # would a local object:
    stimPacketBuffer = websockets_client['stimPacketRx']

    signalTypeToPlot = 'hifreq' # ['hi-res', 'hifreq', 'stim']

    '''mapFileName = 'dummy'
    if mapFileName is not None:
        electrodeMapDF = mapToDF(f'./ripple_map_files/{mapFileName}.map')
        channel_group = {
            'channels': [idx for idx, item in enumerate(channel_info)],
            'geometry': [[100 * (idx % 3 - 1), 100 * idx] for idx, item in enumerate(channel_info)]
            }'''

    channel_info = txBuffer.outputs['hifreq'].params['channel_info']
    channel_group = {
        'channels': [idx for idx in range(len(channel_info))],
        'geometry': [
            (int(entry['xcoords'] / 100), int(entry['ycoords'] / 100))
            for entry in channel_info]
        }

    triggerAcc = RippleTriggerAccumulator()
    triggerAcc.configure(channel_group=channel_group, debounce=500e-3)
    triggerAcc.inputs['signals'].connect(txBuffer.outputs[signalTypeToPlot])
    triggerAcc.inputs['events'].connect(txBuffer.outputs['stim'])
    triggerAcc.inputs['stim_packets'].connect(stimPacketBuffer.outputs['stim_packets'])

    triggerAcc.initialize()
    win = RippleTriggeredWindow(triggerAcc, refreshRateHz=10)
    win.show()
    
    # start nodes
    win.start_refresh()
    triggerAcc.start()

    print(f'{__file__} starting qApp ...')
    app.exec()

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