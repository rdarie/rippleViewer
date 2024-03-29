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
import argparse
#

usage = """Usage:
"""

parser = argparse.ArgumentParser()
parser.add_argument('-pyacq_ip', '--pyacq_server_ip', required=False, help="Sets the server's IP address")
parser.add_argument('-pyacq_p', '--pyacq_server_port', required=False, help="Sets the server's port")
parser.add_argument('-d', '--debug', required=False, type=bool, default=False, help="Flag that bypasses xipppy connection")
parser.add_argument('-m', '--map_file', required=False, type=str, default="dummy", help="Map file to display")
args = parser.parse_args()

pyacqServerOpts = dict(
    ip='127.0.0.1', port="5001"
    )

if args.pyacq_server_ip is not None:
    pyacqServerOpts['ip'] = args.pyacq_server_ip
if args.pyacq_server_port is not None:
    pyacqServerOpts['port'] = args.pyacq_server_port

rpc_addr = f"tcp://{pyacqServerOpts['ip']}:{pyacqServerOpts['port']}"

def main():
    # Start Qt application
    app = pg.mkQApp()
    #
    showSpikes = False
    showScope = True
    showTFR = True
    signalTypesToPlot = ['hifreq'] # ['hi-res', 'hifreq', 'stim']
    
    if showSpikes:
        signalTypesToPlot += ['stim']
        
    # In host/process/thread 2: (you must communicate rpc_addr manually)
    client = pyacq.RPCClient.get_client(rpc_addr)

    # Get a proxy to published object; use this (almost) exactly as you
    # would a local object:
    txBuffer = client['nip0']

    rxBuffer = pyacq.XipppyRxBuffer(
        name='nip_rx0',
        requested_signal_types=signalTypesToPlot
        )
    rxBuffer.configure()
    for signalType in signalTypesToPlot:
        rxBuffer.inputs[signalType].connect(txBuffer.outputs[signalType])
    for signalType in pyacq.ripple_signal_types:
        rxBuffer.outputs[signalType].configure(
            # protocol='tcp', interface='127.0.0.1', transfermode='sharedmem', double=True,
            protocol='inproc', transfermode='sharedmem', double=True,
            # protocol='inproc', transfermode='plaindata', double=True,
            )
    rxBuffer.initialize()

    ephyWin = pyacq.NodeMainViewer(
        node=rxBuffer, debug=False, refreshRateHz=10.,
        window_title=f"Signal viewer ({args.map_file})"
        )

    firstSource = True
    for i, signalType in enumerate(signalTypesToPlot):
        if signalType not in pyacq.ripple_analogsignal_types:
            continue
        if signalType not in rxBuffer.sources:
            continue
        sig_source = rxBuffer.sources[signalType]
        if showScope:
            traceview = ephy.TraceViewer(
                source=sig_source, name='signal_{}'.format(signalType))
            traceview.params_controller.on_automatic_color(cmap_name='Set3')
        if showTFR:
            tfrview = ephy.TimeFreqViewer(
                source=sig_source, scaleogram_type='spectrogram',
                name='timefreq_{}'.format(signalType))
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
                    tabify_with='signal_{}'.format(previousSignalType))
            if showTFR:
                ephyWin.add_view(
                    tfrview, connect_time_change=False,
                    tabify_with='timefreq_{}'.format(previousSignalType))
        previousSignalType = signalType

    firstSource = True
    for i, signalType in enumerate(signalTypesToPlot):
        if signalType not in pyacq.ripple_event_types:
            continue
        if signalType not in rxBuffer.sources:
            continue
        sig_source = rxBuffer.sources[signalType]
        if showSpikes:
            spkview = ephy.SpikeTrainViewer(
                source=sig_source, name='spikes_{}'.format(signalType))
            spkview.params_controller.on_automatic_color(cmap_name='Set3')
        if firstSource:
            if showSpikes:
                ephyWin.add_view(
                    spkview, connect_time_change=False,
                    )
            firstSource = False
        else:
            if showSpikes:
                ephyWin.add_view(
                    spkview, connect_time_change=False,
                    tabify_with='spikes_{}'.format(previousSignalType))
        previousSignalType = signalType
        
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