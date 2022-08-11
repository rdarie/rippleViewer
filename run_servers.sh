#!/bin/bash

# activate conda
export ANACONDA_ROOT='/C/Users/Radu/anaconda3'
. "${ANACONDA_ROOT}/etc/profile.d/conda.sh"

conda activate rippleViewer

python pyRippleViewer/run_xipppy_server.py &
python pyRippleViewer/run_websockets_listener.py &

echo "Finished launching processes."