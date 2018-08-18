import time
import flask
import uuid
from apscheduler.schedulers.background import BackgroundScheduler


scheduler = BackgroundScheduler()


app = flask.Flask(__name__)


membership_list = {}


@app.route('/ping')
def ping():
    return flask.jsonify({
        'response': 'pong',
        'node_id': app.node_id,
    })


@app.route('/list')
def show():
    pass


@scheduler.scheduled_job(trigger='interval', seconds=1)
def tick():
    print(time.time())


def start_app():
    app.node_id = uuid.uuid4().hex
    app.run(host='0.0.0.0', port=8080)


if __name__ == '__main__':
    scheduler.start()
    start_app()
