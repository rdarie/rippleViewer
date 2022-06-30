#!/bin/bash

# activate conda
source ~/.bashrc

python main_host_test.py &

sleep 10

python main_client_test.py