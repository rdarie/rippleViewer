# -*- coding: utf-8 -*-
# Copyright (c) 2016, French National Center for Scientific Research (CNRS)
# Distributed under the (new) BSD License. See LICENSE for more info.
"""
Noise generator node

Simple example of a custom Node class that generates a stream of random
values. 

"""

from pyRippleViewer import *
import time

if LOGGING:
    logger = startLogger(__file__, __name__)


def main():
    # Start Qt application
    app = pg.mkQApp()

    # Create a manager to spawn worker process to record and process audio
    # man = pyacq.create_manager()
    #
    # nodegroup_dev = man.create_nodegroup()
    # dev = nodegroup_dev.create_node(
    #     'XipppyBuffer', name='nip0')
    txBuffer = pyacq.XipppyTxBuffer(name='nip0_tx', dummy=True)
    #
    requestedChannels = {
            # 'hi-res': [2, 4],
            # 'hifreq': [2, 4],
            'stim': [chIdx for chIdx in range(0, 32, 5)],
            }

    txBuffer.configure(
        sample_interval_sec=100e-3, sample_chunksize_sec=100e-3,
        buffer_size_sec=5.,
        channels=requestedChannels, verbose=False, debugging=False)
    print(f'txBuffer.present_analogsignal_types = {txBuffer.present_analogsignal_types}')
    for signalType in pyacq.ripple_signal_types:
        txBuffer.outputs[signalType].configure(
            # protocol='inproc', transfermode='sharedmem', double=True
            protocol='tcp', interface='127.0.0.1', transfermode='plaindata', double=True
            )
    txBuffer.initialize()

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
    txBuffer.start()
    triggerAcc.start()
    #
    app.exec()
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
            profilerResultsFileName = getProfilerPath(__file__)
            #
            from pyRippleViewer.profiling import profiling as prf   
            prf.processYappiResults(
                fileName=profilerResultsFileName, folder=profilerResultsFolder,
                minimum_time=yappi_minimum_time, modulesToPrint=yappiModulesToPrint,
                run_time=run_time, metadata=runMetadata)