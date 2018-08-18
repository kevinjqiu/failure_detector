import flask
import uuid


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


if __name__ == '__main__':
    app.node_id = uuid.uuid4().hex
    app.run(host='0.0.0.0', port=8080)
