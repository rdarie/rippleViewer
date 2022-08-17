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
            
    dev = pyacq.XipppyTxBuffer(name='nip0', dummy=args.debug)
    server['nip0'] = dev

    requestedChannels = {
        # 'hi-res': [2, 4],
        # 'hifreq': [chIdx for chIdx in range(64)],
        # 'stim': [chIdx for chIdx in range(0, 8)],
        }

    mapFileName = 'dummy'
    mapFilePath = f'./ripple_map_files/{mapFileName}.map'

    dev.configure(
        sample_interval_sec=100e-3, sample_chunksize_sec=100e-3,
        buffer_size_sec=20., mapFilePath=mapFilePath,
        channels=requestedChannels, verbose=False, debugging=False)

    print(f'dev.present_analogsignal_types = {dev.present_analogsignal_types}')
    for signalType in pyacq.ripple_signal_types:
        dev.outputs[signalType].configure(
            protocol='tcp', interface=pyacqServerOpts['ip'],
            transfermode='sharedmem', double=True,
            # transfermode='plaindata', double=True
            )
    dev.initialize()
    
    win = pyacq.PyacqServerWindow(server=server, winTitle='xipppy server')
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