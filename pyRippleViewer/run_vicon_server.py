
from pyRippleViewer import *
import os, sys, re, socket, time, argparse

if LOGGING:
    logger = startLogger(__file__, __name__)

usage = """Usage:
    python

# Examples:
"""

parser = argparse.ArgumentParser()
parser.add_argument('-pyacq_ip', '--pyacq_server_ip', required=False, help="Sets the server's IP address")
parser.add_argument('-pyacq_p', '--pyacq_server_port', required=False, help="Sets the server's port")
parser.add_argument('-d', '--debug', required=False, type=bool, default=False, help="Flag that bypasses xipppy connection")
args = parser.parse_args()

pyacqServerOpts = dict(
    ip='127.0.0.1', port="5001"
    )
if args.pyacq_server_ip is not None:
    pyacqServerOpts['ip'] = args.pyacq_server_ip
if args.pyacq_server_port is not None:
    pyacqServerOpts['port'] = args.pyacq_server_port

rpc_addr = f"tcp://{pyacqServerOpts['ip']}:{pyacqServerOpts['port']}"

import sys
import re


def main():
    requested_signal_types = ['devices']
    signalTypesToPlot = ['Unnamed Device 20']
    # Start Qt application
    app = pg.mkQApp()
    # Start a server
    print("Starting server at: {}".format(rpc_addr))
    server = pyacq.QtRPCServer(address=rpc_addr)
    host = pyacq.core.Host(name=socket.gethostname(), poll_procs=True)
    server['host'] = host
    print("Running server at: %s" % server.address.decode())
    ####################################################
    viconServer = pyacq.Vicon(
        name='vicon', requested_signal_types=requested_signal_types)
    server['vicon'] = viconServer
    viconServer.configure(
        ip_address="192.168.42.131", port="801",
        output_name_list=signalTypesToPlot)
    ####################################################
    # connect viconServer inputs
    ####################################################
    # configure viconServer outputs
    for outputName, output in viconServer.outputs.items():
        output.configure(
            protocol='tcp', interface='127.0.0.1', transfermode='sharedmem', double=True,
            # protocol='inproc', transfermode='sharedmem', double=True,
            # protocol='inproc', transfermode='plaindata', double=True,
            )
    ####################################################
    viconServer.initialize()
    ####################################################
    win = pyacq.PyacqServerWindow(server=server, winTitle='vicon server')
    win.show()
    ####################################################
    win.start()
    viconServer.start()
    print(f'{__file__} starting qApp...')
    app.exec()
    ####################################################
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