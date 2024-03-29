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
import sys, re, time, argparse

if LOGGING:
    logger = startLogger(__file__, __name__)

usage = """
"""

usage = """Usage:
"""

parser = argparse.ArgumentParser()
parser.add_argument('-pyacq_ip', '--pyacq_server_ip', required=False, default="127.0.0.1", help="Sets the server's IP address")
parser.add_argument('-pyacq_p', '--pyacq_server_port', required=False, default="5001", help="Sets the server's port")
parser.add_argument('-ws_ip', '--websockets_server_ip', required=False, default="192.168.42.1", help="Sets the server's IP address")
parser.add_argument('-ws_p', '--websockets_server_port', required=False, default="7890", help="Sets the server's port")
parser.add_argument('-d', '--debug', required=False, type=bool, default=False, help="Flag that bypasses xipppy connection")
parser.add_argument('-m', '--map_file', required=False, type=str, default="dummy", help="Map file to display")
args = parser.parse_args()

xipppy_rpc_addr = f'tcp://{args.pyacq_server_ip}:{args.pyacq_server_port}'
websockets_rpc_addr = f'tcp://{args.websockets_server_ip}:{args.websockets_server_port}'

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

    channel_info = txBuffer.outputs['hifreq'].params['channel_info']
    channel_group = {
        'channels': [idx for idx in range(len(channel_info))],
        'geometry': [
            (int(entry['xcoords'] / 100), int(entry['ycoords'] / 100))
            for entry in channel_info]
            }

    triggerAcc = RippleTriggerAccumulator(sense_blank_limits=[0, 1e-3], enable_artifact_rejection=True)
    triggerAcc.configure(channel_group=channel_group, debounce=990e-3)
    triggerAcc.inputs['signals'].connect(txBuffer.outputs[signalTypeToPlot])
    triggerAcc.inputs['events'].connect(txBuffer.outputs['stim'])
    triggerAcc.inputs['stim_packets'].connect(stimPacketBuffer.outputs['stim_packets'])

    triggerAcc.initialize()
    win = RippleTriggeredWindow(triggerAcc, refreshRateHz=10, window_title=f"Triggered view ({args.map_file})")
    win.show()
    
    # start nodes
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