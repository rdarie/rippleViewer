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
import sys, re, socket, time
import argparse

if LOGGING:
    logger = startLogger(__file__, __name__)

usage = """Usage:
    python

# Examples:
"""

parser = argparse.ArgumentParser()
parser.add_argument('-ip', '--server_ip', required=False, help="Sets the server's IP address")
parser.add_argument('-p', '--server_port', required=False, help="Sets the server's IP address")
parser.add_argument('-pyacq_ip', '--pyacq_server_ip', required=False, help="Sets the server's IP address")
parser.add_argument('-pyacq_p', '--pyacq_server_port', required=False, help="Sets the server's IP address")
args = parser.parse_args()

webSocketConfOpts = dict(
    server_ip='10.9.145.31', server_port=7890
    # server_ip='192.168.42.1', server_port=7890
    )
if args.server_ip is not None:
    webSocketConfOpts['server_ip'] = args.server_ip
if args.server_port is not None:
    webSocketConfOpts['server_port'] = args.server_port

pyacqServerOpts = dict(
    ip='127.0.0.2', port="5001"
    )
if args.pyacq_server_ip is not None:
    pyacqServerOpts['ip'] = args.pyacq_server_ip
if args.pyacq_server_port is not None:
    pyacqServerOpts['port'] = args.pyacq_server_port
rpc_addr = f"tcp://{pyacqServerOpts['ip']}:{pyacqServerOpts['port']}"

def main():
    # Start Qt application
    app = pg.mkQApp()
    # Start a server
    print("Starting server at: {}".format(rpc_addr))
    server = pyacq.QtRPCServer(address=rpc_addr)
    host = pyacq.core.Host(name=socket.gethostname(), poll_procs=True)
    server['host'] = host
    print("Running server at: %s" % server.address.decode())

    stimPacketRx = pyacq.StimPacketReceiver()
    server['stimPacketRx'] = stimPacketRx

    stimPacketRx.configure(**webSocketConfOpts)
    stimPacketRx.outputs['stim_packets'].configure(
        protocol='tcp', interface=pyacqServerOpts['ip'],
        # transfermode='plaindata', double=True,
        transfermode='sharedmem', double=True,
        )
    stimPacketRx.initialize()
    
    win = pyacq.PyacqServerWindow(server=server, winTitle='websockets listener')
    win.show()
    
    # start nodes
    stimPacketRx.start()
    win.start()

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