from flask import Flask, request, jsonify, render_template
import logging
import json

app = Flask(__name__)
logger = logging.getLogger(__name__)


# Read from ./db/kill.json and ./db/save.json on init
kill_json = None
save_json = None

try:
    with open('./db/kill.json', 'r') as f:
        kill_json = json.load(f)
except OSError as e:
    logger.error(f"Unable to read kill.json: {e}")
    exit(1)

try:
    with open('./db/save.json', 'r') as f:
        save_json = json.load(f)
except OSError as e:
    logger.error(f"Unable to read save.json: {e}")
    exit(1)


def update_kill_save(mode, kill_json, save_json):
    if mode == 'kill':
        kill_json['results'][0]['total'] = '1'
        save_json['results'][0]['total'] = '0'
    elif mode == 'save':
        kill_json['results'][0]['total'] = '0'
        save_json['results'][0]['total'] = '1'
    else:
        raise ValueError(f"Invalid mode: {mode}")
    with open('./db/kill.json', 'w') as f:
        json.dump(kill_json, f)
    with open('./db/save.json', 'w') as f:
        json.dump(save_json, f)
    return kill_json, save_json

@app.route('/')
def index():
    # serve the file at ./html/controller.html
    return render_template('controller.html')


@app.route('/kill', methods=['GET'])
def kill():
    parameters = request.args
    global kill_json
    if request.method == 'GET':
        if 'status' in parameters:
            if int(float(kill_json['results'][0]['total'])) >= 1 and float(kill_json['results'][0]['total']) > float(save_json['results'][0]['total']):
                return "<div class='ahead'>✅</div>"
            else:
                return "<div class='behind'>❌</div>"
        return jsonify(kill_json)

@app.route('/kill', methods=['POST'])
def set_kill_as_lead():
    # logger.info(f"POST /kill")
    global kill_json
    global save_json
    kill_json, save_json = update_kill_save('kill', kill_json, save_json)

    return jsonify(kill_json)

@app.route('/save', methods=['GET'])
def save():
    parameters = request.args
    global save_json
    if request.method == 'GET':
        if 'status' in parameters:
            if int(float(save_json['results'][0]['total'])) >= 1 and float(save_json['results'][0]['total']) > float(kill_json['results'][0]['total']):
                return "<div class='ahead'>✅</div>"
            else:
                return "<div class='behind'>❌</div>"
        return jsonify(save_json)

@app.route('/save', methods=['POST'])
def update_save():
    # logger.info(f"POST /save")
    global kill_json
    global save_json
    kill_json, save_json = update_kill_save('save', kill_json, save_json)
    return jsonify(save_json)

if __name__ == '__main__':
    app.run(debug=True)