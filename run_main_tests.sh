#!/bin/bash

# activate conda
export ANACONDA_ROOT='/E/mambaforge-pypy3'
. "${ANACONDA_ROOT}/etc/profile.d/conda.sh"

conda activate ripple_viewer_env

python pyRippleViewer/run_xipppy_server.py -d True &
# python pyRippleViewer/run_websockets_listener.py &
sleep 10
python pyRippleViewer/run_signal_viewer.py &
# python pyRippleViewer/run_triggered_viewer.py &

echo "Finished launching processes."