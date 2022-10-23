#!/bin/bash

# activate conda
export ANACONDA_ROOT='/c/anaconda3'
. "${ANACONDA_ROOT}/etc/profile.d"/conda.sh

conda deactivate
conda activate isi_env

python pyRippleViewer/run_xipppy_server.py -pyacq_ip 127.0.0.1 -pyacq_p 5001 -d True -m boston_sci_caudal &
python pyRippleViewer/run_xipppy_server.py -pyacq_ip 127.0.0.1 -pyacq_p 5002 -d True -m boston_sci_rostral &
#
python pyRippleViewer/run_websockets_listener.py -pyacq_ip 127.0.0.1 -pyacq_p 5001 -ws_ip 127.0.0.1 -ws_p 5003 &
python pyRippleViewer/run_websockets_listener.py -pyacq_ip 127.0.0.1 -pyacq_p 5002 -ws_ip 127.0.0.1 -ws_p 5003 &

echo "Finished launching processes."