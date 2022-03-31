#!/bin/bash

source ./process.sh

PORT=$(python prototype_state.py get_port "$1")
portstop "$PORT"
