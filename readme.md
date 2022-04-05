Useful stuff for doing a demo on Replicated State Machines, [@arangodb](https://github.com/arangodb/arangodb). 

Before using these scripts edit your `arangodb` path in `process.sh`. Make sure there's a `build` folder in there.

- restart.sh - restarts the cluster and creates a state machine
- watchlog.sh - replicated log monitoring
- chaos.sh - start inserting entries
- stop.sh \[participant\] - sends SIGSTOP to a participant
- cont.sh \[participant\] - sends SIGCONT to a participant
- stop-leader.sh - stops current leader
- set-leader.sh \[participant\] - replaces the leader with a participant already present in the log
- replace.sh \[old\] \[new\] - replace old participant with new
- unused.sh - list unused participants

Demo
====
For extra fun do `python3 painter.py`, but this is optional

1) start a cluster and create a replicated state
2) start `watchlog`
3) start `chaos`
4) kill a follower
5) bring the follower back up
6) kill the leader - successful election
7) kill the leader again - unsuccessful election
8) bring back one of the dead servers - successful election
9) bring back the other dead server
10) replace the leader with an unused server
11) replace all
