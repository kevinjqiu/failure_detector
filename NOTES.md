* Need a really simple HTTP server framework, so I don't have to use raw sockets and deal with the intricacies of using raw sockets
* For simplicity, all messages are formatted in JSON


HeartBeat Style Failure Detector with Gossip
============================================

    $ inv bootstrap --size=3

    $ inv start-node ... -p <pick one from network.json>

    $ inv list-nodes

    $ inv list-members <random node>

    expected to see the new node's heartbeat being gossipped
