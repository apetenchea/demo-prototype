#!/bin/bash

source ./process.sh

PORT=$(python3 prototype_state.py get_port "$1")
portcont "$PORT"
