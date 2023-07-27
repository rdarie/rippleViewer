# -*- coding: utf-8 -*-
# Copyright (c) 2016, French National Center for Scientific Research (CNRS)
# Distributed under the (new) BSD License. See LICENSE for more info.
"""
Noise generator node

Simple example of a custom Node class that generates a stream of random
values. 

"""

import os, pdb
import time

from pyRippleViewer import *

if LOGGING:
    logger = startLogger(__file__, __name__)

import sys
import re
#

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
    showScope = True
    showTFR = True
    requested_signal_types = ['devices']
    signalTypesToPlot = ['ISI-C-0002', 'Delsys ACC', 'Delsys EMG']
    # Start Qt application
    app = pg.mkQApp()
    ####################################################
    viconServer = pyacq.Vicon(
        name='vicon', requested_signal_types=requested_signal_types)
    viconServer.configure(
        ip_address="192.168.30.2", port="801",
        output_name_list=signalTypesToPlot)
    ####################################################
    # configure viconServer outputs
    for outputName in viconServer.outputs:
        output = viconServer.outputs[outputName]
        # print(f"{outputName}: {output.spec['nb_channel']} chans")
        output.configure(
            # protocol='tcp', interface='127.0.0.1', transfermode='sharedmem', double=True,
            protocol='inproc', transfermode='sharedmem', double=True,
            # protocol='inproc', transfermode='plaindata', double=True,
            )
    ####################################################
    viconServer.initialize()

    all_output_names = [
        key
        for key, value in viconServer.outputs.copy().items()]
    signalTypesToPlot = [
        stp
        for stp in signalTypesToPlot
        if stp in all_output_names]
    
    ####################################################
    # connect viconServer inputs
    ####################################################
    rxBuffer = pyacq.ViconRxBuffer(name='vicon_rx0')
    rxBuffer.configure(output_names=signalTypesToPlot, output_dict=viconServer.outputs)
    for outputName in signalTypesToPlot:
        output = viconServer.outputs[outputName]
        rxBuffer.inputs[outputName].connect(output)
    rxBuffer.initialize()
    ######################
    viconServer.start()
    rxBuffer.start()
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