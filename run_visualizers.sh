#!/bin/bash

# activate conda
export ANACONDA_ROOT='/c/anaconda3'
. "${ANACONDA_ROOT}/etc/profile.d"/conda.sh

conda deactivate
conda activate isi_env

python pyRippleViewer/run_signal_viewer.py -pyacq_ip 127.0.0.1 -pyacq_p 5001 -m boston_sci_caudal &
python pyRippleViewer/run_signal_viewer.py -pyacq_ip 127.0.0.1 -pyacq_p 5002 -m boston_sci_rostral &

echo "Finished launching processes."