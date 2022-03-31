#!/bin/bash

source ./process.sh
LEADER=$(python prototype_state.py get_leader)
PORT=$(python prototype_state.py get_port "$LEADER")
portstop "$PORT"
