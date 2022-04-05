#!/bin/bash

source ./process.sh
LEADER=$(python3 prototype_state.py get_leader)
PORT=$(python3 prototype_state.py get_port "$LEADER")
portstop "$PORT"
