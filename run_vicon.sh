#!/bin/bash

# activate conda
export ANACONDA_ROOT='/C/Users/Radu/anaconda3'
. "${ANACONDA_ROOT}/etc/profile.d/conda.sh"

conda activate rippleViewer

python pyRippleViewer/run_vicon_server.py &
sleep 30
python pyRippleViewer/run_vicon_viewer.py

echo "Finished launching processes."