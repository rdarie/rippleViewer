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
python host_server.py tcp://10.0.0.100:5000
python host_server.py tcp://10.0.0.100:*
"""

if len(sys.argv) == 2:
    rpc_addr = sys.argv[1]
else:
    rpc_addr = 'tcp://127.0.0.1:5001'
    
if not re.match(r'tcp://(\*|([0-9\.]+)):(\*|[0-9]+)', rpc_addr):
    sys.stderr.write(usage)
    sys.exit(-1)

def main():
    # Start Qt application
    app = pg.mkQApp()

    # In host/process/thread 2: (you must communicate rpc_addr manually)
    client = pyacq.RPCClient.get_client(rpc_addr)

    # Get a proxy to published object; use this (almost) exactly as you
    # would a local object:
    txBuffer = client['nip0']

    signalTypeToPlot = 'hifreq' # ['hi-res', 'hifreq', 'stim']

    channel_info = txBuffer.outputs['hi-res'].params['channel_info']
    channel_group = {
        'channels': [idx for idx, item in enumerate(channel_info)],
        'geometry': [[0, 100 * idx] for idx, item in enumerate(channel_info)]
        }
    triggerAcc = RippleTriggerAccumulator()
    triggerAcc.configure(channel_group=channel_group)
    triggerAcc.inputs['signals'].connect(txBuffer.outputs[signalTypeToPlot])
    triggerAcc.inputs['events'].connect(txBuffer.outputs['stim'])

    triggerAcc.initialize()
    win = RippleTriggeredWindow(triggerAcc)
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