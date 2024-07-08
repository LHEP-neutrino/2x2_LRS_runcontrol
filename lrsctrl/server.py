import logging
from flask import Flask, request, jsonify
from waitress import serve
import threading, time
from datetime import datetime
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from lrsctrl.config import Config
from lrsctrl.sender import Sender, SENDER_PORT_ADC64, SENDER_PORT_RC
from lrsctrl.metadata import dump_metadata
from lrscfg.client import Client
from lrsctrl.run_calibration import *
import ppulse.client as pp

cl = Client()
app = Flask(__name__)
CUR_RUN = None
CUR_RUN_LOCK = threading.Lock()
FILE_PROCESS_LOCK = threading.Lock()

# Configure logging
logging.basicConfig(level=logging.DEBUG)
app.logger.setLevel(logging.DEBUG)

# Disable logging for watchdog
logging.getLogger('watchdog').setLevel(logging.CRITICAL)

def start_app():
    server_settings = Config().parse_yaml()
    host = server_settings['AppHost']
    port = server_settings['AppPort']
    serve(app, host=host, port=port, _quiet=False)


# Log all received requests
@app.before_request
def log_request_info():
    app.logger.info(f"Received {request.method} request for {request.url}")
    if request.method == 'POST':
        app.logger.info(f"Request data: {request.get_json()}")


# Data run controls
@app.route("/api/start_data_run/", methods=['POST'])
def start_data_run():
    global CUR_RUN
    data = request.get_json()
    CUR_RUN = data
    start_rc()
    return jsonify(None)

@app.route("/api/reset_meta/", methods=['POST'])
def reset_meta():
    global CUR_RUN
    data = request.get_json()
    CUR_RUN = data
    return jsonify(None)

@app.route("/api/stop_data_run/")
def stop_data_run():
    stop_rc()
    time.sleep(10)
    app.logger.info("RUN: Run stopped")
    if file_handler.last_file_path:
        app.logger.debug("Start process last file")
        with FILE_PROCESS_LOCK:
            app.logger.debug("Lock done")
            file_handler.process_file(file_handler.last_file_path)
    app.logger.info("RUN: All files proccessed")
    return jsonify(None)


# Calibration run controls
@app.route("/api/start_calib_run/")
def start_calib_run():
    config_dict = Config().parse_yaml()
    pp.set_trig(config_dict["pulser_period"])
    with CUR_RUN_LOCK:
        global CUR_RUN
        CUR_RUN = {
            "run": 0,
            "data_stream": "calibration",
            "run_starting_instance": "lrsctrl"
        }
    app.logger.info("CALIB: Start calib run")
    commands = run_calibration()
    app.logger.info("CALIB: Pulser config files written")
    for i, command in enumerate(commands):
        app.logger.info('CALIB: Run calib run %d of %d: %s' % (i+1, len(commands), command))
        pp.set_channels_file(command)
        start_rc()
        #time.sleep(config_dict["pulser_period"])
        pp.run_trig(config_dict["pulser_duration"])
        append_json_name(command, command)
        stop_rc()
        time.sleep(8)
    time.sleep(10)

    now = datetime.now()
    dt_string = now.strftime("%Y.%m.%d.%H.%M.%S")
    out_file = dt_string + '.json'
    convert_to_adcs(out_file)
    app.logger.info('CALIB: Run finished, ok to cancel')
    
    if file_handler.last_file_path:
        app.logger.debug("Start process last file")
        with FILE_PROCESS_LOCK:
            file_handler.process_file(file_handler.last_file_path)
        app.logger.debug("Done process last file")
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


class FileHandler(FileSystemEventHandler):
    def __init__(self):
        super().__init__()
        self.last_file_path = None

    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith('.data'):
            app.logger.debug(f"New file discoverd {event.src_path}")
            with FILE_PROCESS_LOCK:
                if self.last_file_path:  # Check if there was a previous file
                    self.process_file(self.last_file_path)  # Process the previous file
                self.last_file_path = event.src_path

    def process_file(self, file_path):
        global CUR_RUN
        app.logger.info(f"Process file {file_path}")
        app.logger.debug(CUR_RUN)
        if CUR_RUN:
            meta_args = CUR_RUN
            meta_args["database"] = Config().parse_yaml()["db_path"]
            meta_args["datafile"] = str(file_path)
            dump_metadata(app, meta_args) #also adds entry to LRS runs database
            app.logger.debug("Dump metadata done")
            self.last_file_path = None
        else:
            app.logger.warning("NO RUN INFO for file %s, metadata not created", str(self.last_file_path))


def watch_for_new_files(directory, event_handler):
    observer = Observer()
    observer.schedule(event_handler, directory, recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == "__main__":
    directory_to_watch = '/data/LRS'
    file_handler = FileHandler()
    watcher_thread = threading.Thread(target=watch_for_new_files, args=(directory_to_watch, file_handler))
    watcher_thread.daemon = True
    watcher_thread.start()
    start_app()
