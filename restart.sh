#!/bin/bash

source ./process.sh

shutdownLocalCluster
startLocalCluster
python3 prototype_state.py create_prototype_state