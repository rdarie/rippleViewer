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
from copy import copy, deepcopy

from pyRippleViewer import *

if LOGGING:
    logger = startLogger(__file__, __name__)

import sys, re, argparse

usage = """Usage:
    python pyacq_ripple_host.py [address]

# Examples:
python host_server.py tcp://10.0.0.100:5000
python host_server.py tcp://10.0.0.100:*
"""

parser = argparse.ArgumentParser()
parser.add_argument('-pyacq_ip', '--pyacq_server_ip', required=False, help="Sets the server's IP address")
parser.add_argument('-pyacq_p', '--pyacq_server_port', required=False, help="Sets the server's port")
parser.add_argument('-d', '--debug', required=False, type=bool, default=False, help="Flag that bypasses xipppy connection")
parser.add_argument('-m', '--map_file', required=False, type=str, default="dummy", help="Map file to display")
args = parser.parse_args()

pyacqServerOpts = dict(ip='127.0.0.1', port="5001")

if args.pyacq_server_ip is not None:
    pyacqServerOpts['ip'] = args.pyacq_server_ip
if args.pyacq_server_port is not None:
    pyacqServerOpts['port'] = args.pyacq_server_port

rpc_addr = f"tcp://{pyacqServerOpts['ip']}:{pyacqServerOpts['port']}"

def main():
    showScope = True
    showTFR = True
    signalTypesToPlot = ['Unnamed Device 20']

    # Start Qt application
    app = pg.mkQApp()

    # In host/process/thread 2: (you must communicate rpc_addr manually)
    client = pyacq.RPCClient.get_client(rpc_addr)

    # Get a proxy to published object; use this (almost) exactly as you
    # would a local object:
    viconServer = client['vicon']
    
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
        rxBuffer.inputs[outputName].connect(viconServer.outputs[outputName])

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

    ######################
    ephyWin.show()
    ephyWin.start_viewers()
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