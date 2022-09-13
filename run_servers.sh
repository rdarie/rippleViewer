#!/bin/bash

# activate conda
. "/C/ProgramData/Anaconda3/etc/profile.d/conda.sh"

conda activate rippleViewer

python pyRippleViewer/run_xipppy_server.py &
python pyRippleViewer/run_websockets_listener.py &

echo "Finished launching processes."