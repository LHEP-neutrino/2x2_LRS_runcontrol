from flask import Flask, request, jsonify
from lrsctrl.config import Config
from lrsctrl.sender import Sender, SENDER_PORT_ADC64, SENDER_PORT_RC


app = Flask(__name__)


def start_app():
    server_settings = Config().parse_yaml()
    host = server_settings['AppHost']
    port = server_settings['AppPort']
    app.run(host=host, port=port, debug=True)

#Data run controls
@app.route("/api/start_data_run/")
def start_data_run():
    start_rc()
    return jsonify(None)

@app.route("/api/stop_data_run/")
def stop_data_run():
    stop_rc()
    data = request.get_json()
    #TBD
    return jsonify(None)


#Calibration run controls
@app.route("/api/start_calib_run/")
def start_calib_run():
    #TBD
    return jsonify(None)

@app.route("/api/stop_calib_run/")
def stop_calib_run():
    #TBD
    return jsonify(None)


# DAQ software controls
@app.route("/api/start_adc64/")
def start_adc64():
    Sender(SENDER_PORT_ADC64).msg_send('start_adc64')
    return jsonify(None)

@app.route("/api/stop_adc64/")
def stop_adc64():
    Sender(SENDER_PORT_ADC64).msg_send('stop_adc64')
    return jsonify(None)

@app.route("/api/start_rc/")
def start_rc():
    Sender(SENDER_PORT_RC).msg_send('start_rc')
    return jsonify(None)

@app.route("/api/stop_rc/")
def stop_rc():
    Sender(SENDER_PORT_RC).msg_send('stop_rc')
    return jsonify(None)
