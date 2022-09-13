#!/bin/bash

# activate conda
. "/C/ProgramData/Anaconda3/etc/profile.d/conda.sh"

conda activate rippleViewer

python pyRippleViewer/run_vicon_server.py &
sleep 30
python pyRippleViewer/run_vicon_viewer.py

echo "Finished launching processes."