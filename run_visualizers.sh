#!/bin/bash

# activate conda
export ANACONDA_ROOT='/C/Users/Radu/anaconda3'
. "${ANACONDA_ROOT}/etc/profile.d/conda.sh"

conda activate rippleViewer

# python pyRippleViewer/run_signal_viewer.py &
python pyRippleViewer/run_triggered_viewer.py &

echo "Finished launching processes."