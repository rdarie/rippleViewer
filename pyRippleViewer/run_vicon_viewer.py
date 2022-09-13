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
    # Start Qt application
    app = pg.mkQApp()

    # In host/process/thread 2: (you must communicate rpc_addr manually)
    # client = pyacq.RPCClient.get_client(rpc_addr)

    # Get a proxy to published object; use this (almost) exactly as you
    # would a local object:
    # viconServer = client['vicon']
    ####################################################
    viconServer = pyacq.Vicon(name='vicon')
    viconServer.configure()
    ####################################################
    # connect viconServer inputs
    ####################################################
    # configure viconServer outputs
    for outputName, output in viconServer.outputs.items():
        ## print(f"{outputName}: {output.spec['nb_channel']} chans")
        output.configure(
            # protocol='tcp', interface='127.0.0.1', transfermode='sharedmem', double=True,
            protocol='inproc', transfermode='sharedmem', double=True,
            # protocol='inproc', transfermode='plaindata', double=True,
            )
    ####################################################
    rxBuffer = pyacq.ViconRxBuffer(name='vicon_rx0')
    rxBuffer.configure(output_dict=viconServer.outputs)

    for outputName, output in viconServer.outputs.items():
        rxBuffer.inputs[outputName].connect(output)

    rxBuffer.initialize()

    ephyWin = pyacq.NodeMainViewer(
        node=rxBuffer, debug=False, refreshRateHz=10.)

    firstSource = True
    for inputName, thisInput in rxBuffer.inputs.items():
        if inputName not in rxBuffer.sources:
            continue
        sig_source = rxBuffer.sources[inputName]
        if showScope:
            traceview = ephy.TraceViewer(
                source=sig_source, name='signal_{}'.format(inputName))
            traceview.params_controller.on_automatic_color(cmap_name='Set3')
        if showTFR:
            tfrview = ephy.TimeFreqViewer(
                source=sig_source, scaleogram_type='spectrogram',
                name='timefreq_{}'.format(inputName))
        if firstSource:
            ephyWin.set_time_reference_source(sig_source)
            if showScope:
                ephyWin.add_view(
                    traceview, connect_time_change=False,
                    )
            if showTFR:
                ephyWin.add_view(
                    tfrview, connect_time_change=False,
                    )
            firstSource = False
        else:
            if showScope:
                ephyWin.add_view(
                    traceview, connect_time_change=False,
                    tabify_with='signal_{}'.format(previousInputName))
            if showTFR:
                ephyWin.add_view(
                    tfrview, connect_time_change=False,
                    tabify_with='timefreq_{}'.format(previousInputName))
        previousInputName = inputName
    ephyWin.show()
    ephyWin.start_viewers()
    rxBuffer.start()
    viconServer.start()
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