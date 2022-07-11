import yappi
from profiling_opts import runProfiler, LOGGING, logFormatDict

from datetime import datetime as dt
import os
import logging
import time
import pdb
from pathlib import Path

now = dt.now()

if LOGGING:
    pathHere = Path(__file__)
    thisFileName = pathHere.stem
    logFileDir = pathHere.resolve().parent.parent
    logFileName = os.path.join(
        logFileDir, 'logs',
        f"{thisFileName}_{now.strftime('%Y_%m_%d_%M%S')}.log"
        )
    logging.basicConfig(
        filename=logFileName,
        **logFormatDict
        )
    logger = logging.getLogger(__name__)

from pyRippleViewer import *

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
        server = pyacq.RPCServer(address=rpc_addr)
        server.run_lazy()
        host = pyacq.core.Host(name=socket.gethostname(), poll_procs=True)
        server['host'] = host
        print("Running server at: %s" % server.address.decode())

        # Create a xipppy buffer node
        dev = pyacq.XipppyTxBuffer(name='nip0', dummy=True)
        server['nip0'] = dev

        requestedChannels = {
            # 'hi-res': [2, 4],
            # 'hifreq': [chIdx for chIdx in range(64)],
            # 'stim': [chIdx for chIdx in range(0, 8)],
            }

        dev.configure(
            sample_interval_sec=100e-3, sample_chunksize_sec=100e-3,
            buffer_size_sec=5.,
            channels=requestedChannels, verbose=False, debugging=False)
        print(f'dev.present_analogsignal_types = {dev.present_analogsignal_types}')
        for signalType in pyacq.ripple_signal_types:
            dev.outputs[signalType].configure(
                protocol='tcp', interface='127.0.0.1', transfermode='sharedmem', double=True
                # protocol='tcp', interface='127.0.0.1', transfermode='plaindata', double=True
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