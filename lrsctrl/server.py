from flask import Flask, request, jsonify
from lrsctrl.config import Config
from lrsctrl.sender import Sender, SENDER_PORT_ADC64, SENDER_PORT_RC
from lrsctrl.metadata import dump_metadata
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import os, threading, time


app = Flask(__name__)
CUR_RUN = None
event_handler = None


def start_app():
    server_settings = Config().parse_yaml()
    host = server_settings['AppHost']
    port = server_settings['AppPort']
    app.run(host=host, port=port, debug=True)
    #serve(app, host="0.0.0.0", port=port)

#Data run controls
@app.route("/api/start_data_run/", methods=['POST'])
def start_data_run():
    global CUR_RUN
    start_rc()
    data = request.get_json()
    CUR_RUN = data
    return jsonify(None)

@app.route("/api/stop_data_run/")
def stop_data_run():
    stop_rc()
    time.sleep(10)
    global event_handler
    if event_handler.last_file_path:
        event_handler.process_file(event_handler.last_file_path)
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

class FileHandler(FileSystemEventHandler):
    def __init__(self):
        super().__init__()
        self.last_file_path = None

    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith('.data'):
            if self.last_file_path:  # Check if there was a previous file
                self.process_file(self.last_file_path)  # Process the previous file
            self.last_file_path = event.src_path

    def process_file(self, file_path):
        global CUR_RUN
        if CUR_RUN:
            meta_args = CUR_RUN
            meta_args["datafile"] = file_path
            dump_metadata(meta_args)
            self.last_file_path = None
        else:
            print("NO RUN INFO for file ",self.last_file_path," metadata not created")

def watch_for_new_files(directory):
    global event_handler
    event_handler = FileHandler()
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
    watcher_thread = threading.Thread(target=watch_for_new_files, args=(directory_to_watch,))
    watcher_thread.daemon = True
    watcher_thread.start()
    start_app()
