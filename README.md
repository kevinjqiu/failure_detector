Failure Detector
================

Currently implements a heartbeat-style failure detector using gossip.


Install
=======

    pipenv install

Usage
=====

The implementation is in [`node.py`](node.py).  Simulation tasks are provided in [`tasks.py`](tasks.py).

## Bootstrap a cluster

    inv up

e.g.,

    $ inv up
    Starting node: 127.0.1.1:64706 with peers 127.0.1.1:48615,127.0.1.1:51053
    Starting node: 127.0.1.1:48615 with peers 127.0.1.1:64706,127.0.1.1:51053
    Starting node: 127.0.1.1:51053 with peers 127.0.1.1:64706,127.0.1.1:48615

This starts up a cluster of 3 nodes.  You can change the bootstrap nodes by using `--size` param:

    inv up --size 5

## Show membership list

    inv list-members

e.g.,

    $ inv list-members
    Node: 127.0.1.1:64706
    ================================================================
    id                 last_heartbeat    last_timestamp  status
    ---------------  ----------------  ----------------  --------
    127.0.1.1:64706                26        1534912136  alive
    127.0.1.1:48615                26        1534912136  alive
    127.0.1.1:51053                26        1534912136  alive

    Node: 127.0.1.1:48615
    ================================================================
    id                 last_heartbeat    last_timestamp  status
    ---------------  ----------------  ----------------  --------
    127.0.1.1:48615                26        1534912136  alive
    127.0.1.1:64706                26        1534912136  alive
    127.0.1.1:51053                26        1534912136  alive

    Node: 127.0.1.1:51053
    ================================================================
    id                 last_heartbeat    last_timestamp  status
    ---------------  ----------------  ----------------  --------
    127.0.1.1:51053                26        1534912136  alive
    127.0.1.1:64706                26        1534912136  alive
    127.0.1.1:48615                26        1534912136  alive

This shows the membership list of all nodes in the cluster.  You may want to constantly monitor this membership list by using `watch`:

    watch inv list-members

## Add a new node to the cluster

    inv add-node

This will spawn a new node on a random port and pick a random peer in the existing network as its peer.  Because all the other peers are connected, the new node will eventually have the same membership list as others via gossip.

    $ inv add-node
    Starting node: 127.0.1.1:36522 with peers 127.0.1.1:64706

## Kill a node

    inv kill --node-id=<host:port>

to kill a specific node, or

    inv kill

to kill a random node.

Observe `watch inv list-members` that the membership list of other nodes will eventually have the killed node removed and the same list gossipped across the network to all nodes.

# Demo

[![asciicast](https://asciinema.org/a/WA7oDFiBKk9DiSh5CPrpsB8f2.png)](https://asciinema.org/a/WA7oDFiBKk9DiSh5CPrpsB8f2)
