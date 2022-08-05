from pyRippleViewer import *
import os, sys, re, socket, time

if LOGGING:
    logger = startLogger(__file__, __name__)


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
    # Start Qt application
    app = pg.mkQApp()
    # Start a server
    print("Starting server at: {}".format(rpc_addr))
    server = pyacq.QtRPCServer(address=rpc_addr)
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
        sample_interval_sec=100e-3, sample_chunksize_sec=50e-3,
        buffer_size_sec=10.,
        channels=requestedChannels, verbose=False, debugging=False)
    print(f'dev.present_analogsignal_types = {dev.present_analogsignal_types}')
    for signalType in pyacq.ripple_signal_types:
        dev.outputs[signalType].configure(
            protocol='tcp', interface='127.0.0.1', transfermode='sharedmem', double=True
            # protocol='tcp', interface='127.0.0.1', transfermode='plaindata', double=True
            )
    dev.initialize()
    
    win = pyacq.XippyServerWindow(server=server)
    win.show()
    ######################
    dev.start()
    win.start()
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