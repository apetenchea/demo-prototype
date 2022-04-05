#!/bin/bash

ARANGODB_FOLDER="/home/apetenchea/work/arangodb/"

# get pid of process listening on port
function portpid() {
  lsof -iTCP:"$1" -sTCP:LISTEN -t
}

# stop process listening on port
function portstop() {
    kill -SIGSTOP $(portpid "$1")
}

# continue process listening on port
function portcont() {
    kill -SIGCONT $(portpid "$1")
}

# kill process listening on port
function portkill() {
    kill -9 $(portpid "$1")
}

# get command info of process opened on port
function portinfo() {
  local cmd=$(portpid "$1")
  ps aux | grep "$cmd"
}

# list server endpoints
function listEndpoints() {
  curl -s http://localhost:8530/_admin/cluster/health | jq ".Health | .[] |= .Endpoint"
}

# shutdown local cluster
function shutdownLocalCluster() {
  pkill -9 arangod
}

# start local cluster
function startLocalCluster() {
  (
    cd $ARANGODB_FOLDER || exit 1
    local servers="${1:-8}";
    bash "$ARANGODB_FOLDER/scripts/startLocalCluster.sh" -d "$servers";
  )
}

