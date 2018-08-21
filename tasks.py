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


@task(pre=[killall])
def bootstrap(ctx, size=3, ip='192.168.1.133'):
    ctx.run('mkdir -p logs')
    ctx.run('rm -f logs/*')
    network_state = read_network_state()
    while len(network_state['peers']) < size:
        port = random.randint(*PORT_RANGE)
        bind = '{}:{}'.format(ip, port)
        if not is_port_available(ip, port):
            print('{} is not available.'.format(bind))
            continue

        network_state['peers'][bind] = {}

    peers = network_state['peers'].keys()

    for peer in peers:
        start_node(ctx, peer, ','.join([p for p in peers if p != peer]))


@task
def start_node(ctx, bind, peers):
    logfile = open('logs/{}.log'.format(bind), 'w')
    args = ['python', 'node.py', '-b', bind, '-p', peers]
    print(args)
    p = Popen(args, stdout=logfile, stderr=logfile)
    network_state = read_network_state()
    network_state['peers'][bind] = {
        'pid': p.pid,
    }
    write_network_state(network_state)


@task
def list_nodes(ctx):
    network_state = read_network_state()
    print(tabulate.tabulate(network_state['peers'].items()))


def list_members_for_node(node_id):
    response = requests.get('http://{}/members'.format(node_id))
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
