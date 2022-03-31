#!/bin/bash

source ./process.sh

shutdownLocalCluster
startLocalCluster
python prototype_state.py create_prototype_state