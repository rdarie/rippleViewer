#!/bin/bash

# activate conda
export ANACONDA_ROOT='/c/anaconda3'
. "${ANACONDA_ROOT}/etc/profile.d"/conda.sh

conda activate isi_env

# python pyRippleViewer/run_vicon_viewer.py -pyacq_ip 127.0.0.1 -pyacq_p 5004 &
python pyRippleViewer/run_triggered_vicon_viewer.py -vicon_ip 127.0.0.1 -vicon_p 5004 -xipppy_ip 127.0.0.1 -xipppy_p 5001 -ws_ip 127.0.0.1 -ws_p 5003

echo "Finished launching processes."