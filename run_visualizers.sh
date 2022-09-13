#!/bin/bash

# activate conda
. "/C/ProgramData/Anaconda3/etc/profile.d/conda.sh"

conda activate rippleViewer

python pyRippleViewer/run_signal_viewer.py &
python pyRippleViewer/run_triggered_viewer.py &

echo "Finished launching processes."