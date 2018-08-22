import requests
import argparse
import time
import flask
import uuid
import threading
import logging
import random
from pytz import utc
from collections import namedtuple
from apscheduler.schedulers.background import BackgroundScheduler


logging.basicConfig(level=logging.INFO)
logging.getLogger('apscheduler.executors.default').setLevel(logging.WARNING)


logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()

app = flask.Flask(__name__)


class MemberInfo:
    def __init__(self, id, last_heartbeat, last_timestamp):
        self.id = id                           # id is in the form of <ip>:<port>
        self.last_heartbeat = last_heartbeat   # last received heartbeat sequence no.
        self.last_timestamp = last_timestamp   # last heartbeat received timestamp
        self.status = 'alive'
        self._lock = threading.RLock()

    def increment_heartbeat(self):
        with self._lock:
            self.last_heartbeat += 1
            self.last_timestamp = int(time.time())

    def update(self, updated_member_info):
        with self._lock:
            if updated_member_info.last_timestamp <= self.last_timestamp:
                return
            if updated_member_info.last_heartbeat <= self.last_heartbeat:
                return
            self.last_heartbeat = updated_member_info.last_heartbeat
            self.last_timestamp = int(time.time())
            self.status = 'alive'

    def set_status(self, status):
        with self._lock:
            self.status = status


class MembershipList:
    def __init__(self):
        self._members = {}  # Type: MemberInfo
        self._lock = threading.RLock()

    def add_or_update(self, id, last_heartbeat, last_timestamp):
        with self._lock:
            if id in self._members:
                member_info = self._members[id]
                member_info.update(MemberInfo(id, last_heartbeat, last_timestamp))
            else:
                self._members[id] = MemberInfo(id, last_heartbeat, last_timestamp)

    def json(self):
        return [
            {
                'id': m.id,
                'last_heartbeat': m.last_heartbeat,
                'last_timestamp': m.last_timestamp,
                'status': m.status,
            }
            for m in self._members.values()
        ]

    def update_one(self, id, update_func):
        if id not in self._members:
            logger.warning('Cannot update node {}: the node is not in the member list'.format(id))
            return

        with self._lock:
            member_info = self._members[id]
            update_func(member_info)

    def update_all(self, membership_list):
        with self._lock:
            for member_to_update in membership_list:
                member_info = MemberInfo(
                    member_to_update['id'],
                    member_to_update['last_heartbeat'],
                    member_to_update['last_timestamp'],
                )
                if not member_to_update['id'] in self._members:
                    self._members[member_to_update['id']] = member_info
                else:
                    existing_member = self._members[member_to_update['id']]
                    existing_member.update(member_info)

    def choose_peers(self, n, exclude=None):
        """Randomly returns at most `n` peers excluding the ones in the `exclude` list """
        exclude = set(exclude or [])
        candidates = [ m for m in self._members if m not in exclude ]
        random.shuffle(candidates)
        return candidates[:n]

    def detect_suspected_nodes(self, threshold, protocol_period):
        now = int(time.time())
        with self._lock:
            for id, member_info in self._members.items():
                if member_info.status != 'alive':
                    continue
                if member_info.last_timestamp < now - (threshold * protocol_period):
                    logger.info('No heartbeat from {} for {} beats, mark it as suspected'.format(id, threshold))
                    member_info.set_status('suspected')

    def remove_dead_nodes(self, threshold, protocol_period):
        now = int(time.time())
        members_to_delete = []
        with self._lock:
            for id, member_info in self._members.items():
                if member_info.status != 'suspected':
                    continue
                if member_info.last_timestamp < now - (threshold * protocol_period):
                    logger.info('No heartbeat from {} for {} beats, remove it from membership list'.format(id,
                                                                                                           threshold))
                    members_to_delete.append(id)

            for id in members_to_delete:
                del self._members[id]
                logger.info('Member {} deleted'.format(id))


membership_list = MembershipList()


@app.route('/members', methods=['POST'])
def receive_heartbeat():
    request_json = flask.request.json
    membership_list.update_all(request_json)
    return flask.jsonify({})


@app.route('/members', methods=['GET'])
def members():
    return flask.jsonify(membership_list.json())


def tick():
    # self heartbeat
    membership_list.update_one(app.node_id,
                               lambda member_info: member_info.increment_heartbeat())
    peers = membership_list.choose_peers(2, exclude=[app.node_id])
    for peer in peers:
        try:
            response = requests.post('http://{}/members'.format(peer), json=membership_list.json())
            logging.debug(response)
        except:
            pass

    membership_list.detect_suspected_nodes(app.suspicion_threshold_beats, app.protocol_period)
    membership_list.remove_dead_nodes(app.failure_threshold_beats, app.protocol_period)


def start_app(node_id):
    app.node_id = node_id
    host, port = node_id.split(':', 1)
    app.run(host=host, port=port)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-b', '--bind', help='Host IP + port to bind the process to')
    parser.add_argument('-p', '--peers', help='Initial peer addresses')
    parser.add_argument('-t', '--protocol-period', type=int, help='Protocol period T in seconds', default=1)
    parser.add_argument('-s', '--suspicion-threshold', type=int,
                        help='How many heartbeats are allowed to miss before the node is put in the "suspected" state',
                        default=5)
    parser.add_argument('-f', '--failure-threshold', type=int,
                        help='How many heartbeats are allowed to miss before the node is deemed "failed" and removed',
                        default=10)
    options = parser.parse_args()

    if not options.bind:
        raise ValueError('--bind must be specified')

    if options.bind.startswith('0.0.0.0'):
        raise ValueError('--bind value must be a specific IP address')

    node_id = options.bind

    membership_list.add_or_update(node_id, 0, int(time.time()))

    if options.peers:
        for peer in options.peers.split(','):
            membership_list.add_or_update(peer, 0, int(time.time()))

    app.protocol_period = options.protocol_period
    app.suspicion_threshold_beats = options.suspicion_threshold
    app.failure_threshold_beats = options.failure_threshold

    logger.info('Protocol Period: {}s'.format(app.protocol_period))
    logger.info('Suspicion Threshold (beats): {}'.format(app.suspicion_threshold_beats))
    logger.info('Failure Threshold (beats): {}'.format(app.failure_threshold_beats))

    scheduler.add_job(tick, trigger='interval', seconds=app.protocol_period, timezone=utc)
    scheduler.start()
    start_app(node_id)
