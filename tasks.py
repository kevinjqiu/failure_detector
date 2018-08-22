import sys
import requests
import os
import json
import random
import tabulate
import socket
from invoke import task
from subprocess import Popen


PORT_RANGE = (30000, 65535)

STATE_FILE = 'network.json'

DEFAULT_IP = '192.168.1.133'


def is_port_available(ip, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex((ip, int(port)))
    return result != 0


def read_network_state():
    if not os.path.exists(STATE_FILE):
        return {'peers': {}}

    with open(STATE_FILE) as f:
        return json.loads(f.read())


def write_network_state(new_state):
    with open(STATE_FILE, 'w') as f:
        f.write(json.dumps(new_state, indent=4))


@task
def killall(ctx):
    state = read_network_state()
    for id, peer in state['peers'].items():
        ctx.run('kill {}'.format(peer['pid']), warn=True, echo=True)
    write_network_state({'peers': {}})


@task
def kill(ctx, id=None):
    """Kill a node given the id.  If id is not specified, kill a random node"""
    state = read_network_state()
    if id is None:
        candidates = [p for p in state['peers'].values() if p.get('status') != 'killed']
        if len(candidates) == 0:
            print('No nodes to kill')
            return

        peer = random.choice(candidates)
        return kill(ctx, id=peer['bind'])

    peer = state['peers'].get(id)
    if not peer:
        print('{} is not present in the network'.format(peer))
        return
    if peer.get('status') == 'killed':
        print('{} is already killed'.format(peer))
    print('Kill peer {}'.format(peer))
    ctx.run('kill {}'.format(peer['pid'], warn=True, echo=True))
    peer['status'] = 'killed'
    write_network_state(state)


def next_random_bind(ip, max_retries=10):
    counter = 0
    while counter < max_retries:
        port = random.randint(*PORT_RANGE)
        bind = '{}:{}'.format(ip, port)
        if not is_port_available(ip, port):
            print('{} is not available.'.format(bind))
            counter += 1
            continue
        return bind
    print('No port available after {} retries'.format(max_retries))
    return None


@task(pre=[killall])
def up(ctx, size=3, ip=DEFAULT_IP):
    """Start up a cluster locally"""
    ctx.run('mkdir -p logs')
    ctx.run('rm -f logs/*')
    network_state = read_network_state()
    while len(network_state['peers']) < size:
        bind = next_random_bind(ip)
        if not bind:
            return

        network_state['peers'][bind] = {}

    peers = network_state['peers'].keys()

    for peer in peers:
        start_node(peer, ','.join([p for p in peers if p != peer]))


def start_node(bind, peers):
    outfile = open('logs/{}.log'.format(bind), 'w')
    errfile = open('logs/{}-err.log'.format(bind), 'w')
    args = ['python', 'node.py', '-b', bind, '-p', peers]
    print('Starting node: {} with peers {}'.format(bind, peers))
    p = Popen(args, stdout=outfile, stderr=errfile)
    network_state = read_network_state()
    network_state['peers'][bind] = {
        'bind': bind,
        'pid': p.pid,
    }
    write_network_state(network_state)


@task
def add_node(ctx, ip=DEFAULT_IP):
    """Add a node to the cluster"""
    network_state = read_network_state()
    peers = [peer for peer in network_state['peers'].values() if peer.get('status') != 'killed']
    if len(peers) == 0:
        print('No available peers.')
        return

    peer = random.choice(peers)
    bind = next_random_bind(ip)
    if not bind:
        return

    start_node(bind, peer['bind'])


@task
def list_nodes(ctx):
    network_state = read_network_state()
    print(tabulate.tabulate(network_state['peers'].items()))


def list_members_for_node(node_id):
    try:
        response = requests.get('http://{}/members'.format(node_id))
    except requests.exceptions.ConnectionError:
        print('Node is down')
    else:
        response_json = response.json()
        headers = {}
        if len(response_json) > 1:
            headers = {k:k for k in response_json[0].keys()}
        print(tabulate.tabulate(response_json, headers=headers))


@task
def list_members(ctx, node_id=None):
    if node_id is not None:
        list_members_for_node(node_id)
        return

    network_state = read_network_state()
    for id, peer in network_state['peers'].items():
        print('Node: {}'.format(id))
        print('=' * 64)
        list_members_for_node(id)
        print()
