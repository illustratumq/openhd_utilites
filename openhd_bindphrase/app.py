from flask import Flask, request, redirect, render_template, jsonify, send_file, session
import re
import os
import json
import subprocess
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY")  
DEV_PASSWORD = os.environ.get("DEV_PASSWORD")   

path = '/boot/openhd/'
home = '/home/openhd/'
conf_path = '/home/openhd/'
config_filename = 'openhd_custom_params.json'
base_params_path = '/home/openhd/base_wb_params.json'

# conf_path = './'
# path = ''
# home = './'
# base_params_path = './base_wb_params.json'
# config_filename = 'openhd_custom_params.json'

HOME_IP = "192.168.3.1"

@app.route('/captive.apple.com')
@app.route('/connecttest.txt')
@app.route('/library/test/success.html')
@app.route('/hotspot-detect.html')
@app.route('/connectivity-check.html')
@app.route('/check_network_status.txt')
@app.route('/ncsi.txt')
@app.route('/fwlink')
@app.route('/gen_204')
@app.route('/generate_204')
def captive_portal_redirect():
    host = request.headers.get('Host', '')
    print(host, 'captive')
    return redirect(f"http://{HOME_IP}/", code=302)

def update_json_data(file_path, data):
    try:
        with open(file_path, 'r') as f:
            json_data = json.load(f)
    except Exception as e:
        json_data = {
            "channels": [5745],
            "rc_channel": 10,
            "encryption": "False"
        }
    
    if 'channels' in data.keys():
        data['channels'] = sorted(data['channels'])
    json_data.update(data)
    with open(file_path, 'w') as f:
        json.dump(json_data, f, indent=4)
    

@app.route('/redirect')
@app.route('/')
def index():
    if 'password.txt' not in os.listdir(home):
        current_phrase = 'Not defined password.txt'
    else:
       with open(f'{home}password.txt', 'r') as f:
           current_phrase = f.read()
    is_air = "air.txt" not in os.listdir("/boot/openhd")
    return render_template('index.html', current_phrase=current_phrase, is_air=is_air, dev_unlocked=dev_unlocked()), 200

def dev_unlocked() -> bool:
    return bool(session.get("dev_unlocked", False))

def require_dev_login(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not dev_unlocked():
            return jsonify({"error": "auth required"}), 401
        return fn(*args, **kwargs)
    return wrapper

@app.post("/dev-login")
def dev_login():
    data = request.get_json(silent=True) or {}
    if str(data.get("password", "")) == DEV_PASSWORD:
        session["dev_unlocked"] = True
        return jsonify({"status": "ok"})
    return jsonify({"status": "error"}), 401

@app.post("/dev-logout")
def dev_logout():
    session.pop("dev_unlocked", None)
    return jsonify({"status": "ok"})

@app.route('/save-encryption', methods=['POST'])
def save_encryption():
    update_json_data(f"{conf_path}{config_filename}", request.json)
    return jsonify({'status': 'success'})

@app.route('/save-feature', methods=['POST'])
def save_feature():
    update_json_data(f"{conf_path}{config_filename}", request.json)
    return jsonify({'status': 'success'})

def check_param_in_request(param_name: str, request):
    return param_name in list(request.json.keys())

@app.route('/save-frequencies', methods=['POST'])
def save_frequencies():
    try:
        data = request.json
        data = data if len(data["channels"]) > 0 else data.update({"channels": [5745]})
        if check_param_in_request("fec_value", request):
            data["fec_percent_1"] = str(request.json["fec_value"]).split(",")[0]
            data["fec_percent_2"] = str(request.json["fec_value"]).split(",")[1]
            data["fec_percent_3"] = str(request.json["fec_value"]).split(",")[2]
        update_json_data(f"{conf_path}{config_filename}", request.json)
        update_json_data(base_params_path, {"wb_frequency": request.json.get("base_freq", 5745)})
        if check_param_in_request("wb_air_mcs_index", request):
            update_json_data(base_params_path, {"wb_air_mcs_index": int(request.json.get("mcs_value", 9))})
        if check_param_in_request("rc_channel_mcs", request):
            update_json_data(base_params_path, {"wb_mcs_index_via_rc_channel": int(request.json.get("rc_channel_mcs", 10))})
        return jsonify({'status': 'success'})
    except Exception as error:
        return jsonify({'status': f'Помилка {error}'})

@app.route('/get-frequencies', methods=['GET'])
def get_frequencies():
    try:
        with open(f'{conf_path}{config_filename}', 'r') as f:
            data = json.load(f)
        return jsonify(data)
    except Exception as e:
        return jsonify({"channels": []})


@app.route('/save', methods=['POST'])
def save():
    data = request.json
    bind_phrase = data.get('bind_phrase')
    if bind_phrase:
        with open(f'{home}password.txt', 'w') as f:
            f.write(bind_phrase)
        os.system(f'sudo cp {home}password.txt {path}password.txt')
        with open(f'{home}password.txt', 'w') as f:
            new_b = ['*' for i in range(len(bind_phrase))]
            new_b[0] = bind_phrase[0]
            new_b[-1] = bind_phrase[-1]
            new_b = ''.join(new_b)
            f.write(new_b)
        return jsonify({'status': 'success'})
    return jsonify({'status': 'error', 'message': 'No bind phrase provided'})

@app.route('/usb-devices', methods=['GET'])
def list_usb_devices():
    try:
        result = subprocess.check_output(['lsusb'], text=True)
        return jsonify({"devices": result.strip()})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/reboot', methods=['POST'])
def reboot():
    os.system('sudo reboot')
    return jsonify({'status': 'rebooting'})

@app.route('/get-file/<filename>', methods=['GET'])
@require_dev_login
def get_file(filename):
    try:
        way_to_file = ""
        if filename == "openhd":
            return jsonify({'content': "Файл доступний для скачування. Для заміни образу скористайтесь завантажувачем нижче"})
        elif filename == "config":
            way_to_file = "/boot/config.txt"
        else:
            way_to_file = f"/home/openhd/{filename}.json"
        with open(way_to_file, 'r') as f:
            content = f.read()
        return jsonify({'content': content})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/save-file/<filename>', methods=['POST'])
@require_dev_login
def save_file(filename):
    try:
        way_to_file = ""
        if filename == "openhd":
            return jsonify({'content': "Файл доступний для скачування. Для заміни образу скористайтесь завантажувачем нижче"})
        elif filename == "config":
            way_to_file = "/boot/config.txt"
        else:
            way_to_file = f"/home/openhd/{filename}.json"
        content = request.json.get('content')
        with open(way_to_file, 'w') as f:
            f.write(content)
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download-file/<filename>', methods=['GET'])
@require_dev_login
def download_file(filename):
    try:
        way_to_file = ""
        if filename == "openhd":
            return send_file('/usr/local/bin/openhd', as_attachment=True)
        elif filename == "config":
            way_to_file = "/boot/config.txt"
        else:
            way_to_file = f"/home/openhd/{filename}.json"
        return send_file(way_to_file, as_attachment=True)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/upload-image', methods=['POST'])
@require_dev_login
def upload_image():
    try:
        image = request.files['image']
        image.save('/home/openhd/openhd')
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
if __name__ == "__main__":
    os.system('sudo iptables -t nat -A PREROUTING -p tcp --dport 80 -j REDIRECT --to-port 5000')
    app.run(host="192.168.3.1", port=5000, debug=True)
    # app.run(host="127.0.0.1", port=5000, debug=True)

