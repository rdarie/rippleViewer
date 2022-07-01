import yappi
from profiling_opts import runProfiler, LOGGING

from datetime import datetime as dt
import os
import logging
import time

now = dt.now()

if LOGGING:
    logging.basicConfig(
        filename='..\logs\{}_{}.log'.format(
            os.path.splitext(os.path.basename(__file__))[0].replace('__', ''), now.strftime('%Y%m%d%H%M')),
        level=logging.INFO)
    logger = logging.getLogger(__name__)

import pyRippleViewer
from pyRippleViewer import pyqtgraph as pg
from pyRippleViewer import ephyviewer as ephy
from pyRippleViewer import pyacq as pq

import os, sys, re, socket

usage = """Usage:
    python pyacq_ripple_host.py [rpc_addr]

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
    try:
        # Start a server
        print("Starting server at: {}".format(rpc_addr))
        server = pq.RPCServer(address=rpc_addr)
        server.run_lazy()
        host = pq.core.Host(name=socket.gethostname(), poll_procs=True)
        server['host'] = host
        print("Running server at: %s" % server.address.decode())

        # Create a xipppy buffer node
        dev = pq.XipppyTxBuffer(
            name='nip0', dummy=True)
        server['nip0'] = dev

        requestedChannels = {
            # 'hi-res': [2, 3, 12],
            # 'hifreq': [2, 3, 12],
            # 'stim': [chIdx for chIdx in range(0, 32, 3)],
            }

        dev.configure(
            sample_interval_sec=100e-3, sample_chunksize_sec=100e-3,
            buffer_padding_sec=500e-3,
            channels=requestedChannels, verbose=False, debugging=False)
        for signalType in pq.ripple_signal_types:
            dev.outputs[signalType].configure(
                # protocol='tcp', interface='127.0.0.1', transfermode='sharedmem', double=True
                protocol='tcp', interface='127.0.0.1', transfermode='plaindata', double=True
                )
        dev.initialize()
        dev.start()
        ######################
        server.run_forever()
        ######################
    finally:
        print('Closing server...')
        server.close()

if __name__ == '__main__':
    if runProfiler:
        dateStr = now.strftime('%Y%m%d')
        timeStr = now.strftime('%H%M')
        profilerResultsFileName = '{}_{}_pid_{}'.format(
            __file__.split('.')[0], timeStr, os.getpid())
        profilerResultsFolder = '../yappi_profiler_outputs/{}'.format(dateStr)
        ##
        yappiClockType = 'cpu'
        yappi.set_clock_type(yappiClockType) # Use set_clock_type("wall") for wall time
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
            ###
            minimum_time = 1e-1
            modulesToPrint = [pq, ephy, pg]  # [pq, ephy, pg]
            runMetadata = {}
            from pyRippleViewer.profiling import profiling as prf   
            prf.processYappiResults(
                fileName=profilerResultsFileName, folder=profilerResultsFolder,
                minimum_time=minimum_time, modulesToPrint=modulesToPrint,
                run_time=run_time, metadata=runMetadata)