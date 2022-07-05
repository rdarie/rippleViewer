#!/bin/bash

# activate conda
. "${HOME}/opt/anaconda3/etc/profile.d/conda.sh"
conda activate rippleViewer

python main_host_test.py &

sleep 10

python main_client_test.py