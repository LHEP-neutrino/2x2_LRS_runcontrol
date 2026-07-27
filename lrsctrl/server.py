import logging
from flask import Flask, request, jsonify
from waitress import serve
import threading, time
import os
import json
from datetime import datetime


from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from lrsctrl.sender import Sender, SENDER_PORT_ADC64, SENDER_PORT_RC
from lrsctrl.metadata import dump_metadata, get_afi_config
from lrscfg.client import Client
from lrscfg.config import Config
from lrscfg.set_SIPMs import start_SiPMmoniotoring, stop_SiPMmoniotoring, set_SIPM, set_SiPM_individually
import lrsctrl.utils as utils
import ppulse.client as pp
import lrsctrl.pulser_config_maker as pp_config

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
    # Pull AFI JSONs now (at run start) and store them in the current run info
    try:
        afi_jsons = get_afi_config()
        # store the dict under a single key so metadata writer can pick it up
        CUR_RUN['afi_jsons'] = afi_jsons
    except Exception as e:
        app.logger.warning(f"Failed to load AFI configs at run start: {e}")

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
    app.logger.info("CALIB: Start calib run")
    run_info = utils.Run_Info(app)

    config_dict = Config().parse_yaml()
    app.logger.debug(f"CALIB: Set the pulser period: {config_dict['pulser_period']} ms")
    pp.set_trig(config_dict["pulser_period"])

    with CUR_RUN_LOCK:
        global CUR_RUN
        CUR_RUN = {
            "run": 0,
            "data_stream": "calibration",
            "run_starting_instance": "lrsctrl"
        }

    app.logger.info("CALIB: Get afi config")
    try:
        afi_jsons = get_afi_config()
        # store the dict under a single key so metadata writer can pick it up
        CUR_RUN['afi_jsons'] = afi_jsons
    except Exception as e:
        app.logger.warning(f"Failed to load AFI configs at run start: {e}")

    configs_led, configs_sipmPS = utils.make_calib_files(app)
    app.logger.info("CALIB: Pulser and SiPM config files written")
    # app.logger.info(f"CALIB: Pulser files {configs_led}")
    # app.logger.info(f"CALIB: sipmPS files {configs_sipmPS}")


    # return jsonify(None)

    stop_SiPMmoniotoring(logger=app.logger)
    app.logger.info("CALIB: SiPM bias voltage monitoring stopped")
    
    for i, (config_led, config_sipmPS) in enumerate(zip(configs_led, configs_sipmPS)):
        app.logger.info(f'CALIB: ~~~~~ Start calib run {i} ({i+1}/{len(configs_led)}) ~~~~~')

        pp.set_channels_file(config_led)
        app.logger.info(f'CALIB: Pulser channels set')
        set_SIPM(config_sipmPS, manage_monitoring=False, logger=app.logger)
        app.logger.info(f'CALIB: SiPM bias voltage channels set')

        start_rc()
        app.logger.debug(f'CALIB: ~~~ Run started ~~~')
        time.sleep(8)
        time.sleep(config_dict["pulser_period"])
        pp.run_trig(config_dict["pulser_duration"])
        app.logger.debug(f'CALIB: Pulser finished')
        stop_rc()
        app.logger.debug(f'CALIB: ~~~ Run stopped ~~~')

        run_info.append_subrun_calib(i, config_led, config_sipmPS)
        time.sleep(8)

        # if i>2:
        #     break

    time.sleep(10)
    start_SiPMmoniotoring(logger=app.logger)
    app.logger.info("CALIB: SiPM bias voltage monitoring restored")

    run_info.write_run_info()
    app.logger.info('CALIB: ~~~~~~~ Run finished, run info written ~~~~~~~')
    
    if file_handler.last_file_path:
        app.logger.debug("Start process last file")
        with FILE_PROCESS_LOCK:
            file_handler.process_file(file_handler.last_file_path)
        app.logger.debug("Done process last file")
    return jsonify(None)

# Calibration run controls
@app.route("/api/start_pulser_scan/")
def start_pulser_scan():
    app.logger.info("CALIB: Start pulser scan")
    run_info = utils.Run_Info(app)

    config_dict = Config().parse_yaml()
    app.logger.debug(f"CALIB: Set the pulser period: {config_dict['pulser_period']} ms")
    pp.set_trig(config_dict["pulser_period"])

    with CUR_RUN_LOCK:
        global CUR_RUN
        CUR_RUN = {
            "run": 0,
            "data_stream": "calibration",
            "run_starting_instance": "lrsctrl"
        }

    app.logger.info("CALIB: Get afi config")
    try:
        afi_jsons = get_afi_config()
        # store the dict under a single key so metadata writer can pick it up
        CUR_RUN['afi_jsons'] = afi_jsons
    except Exception as e:
        app.logger.warning(f"Failed to load AFI configs at run start: {e}")

    configs_led = pp_config.make_scan_config(app.logger)
    app.logger.info(f"CALIB: {len(configs_led)} pulser config files written")
    # app.logger.info(f"CALIB: Pulser files {configs_led}")
    # app.logger.info(f"CALIB: sipmPS files {configs_sipmPS}")


    # return jsonify(None)

    # stop_SiPMmoniotoring(logger=app.logger)
    # app.logger.info("CALIB: SiPM bias voltage monitoring stopped")
    
    for i, config_led in enumerate(configs_led):
        app.logger.info(f'CALIB: ~~~~~ Start pulser scan run {i} ({i+1}/{len(configs_led)}) ~~~~~')

        pp.set_channels_file(config_led)
        app.logger.info(f'CALIB: Pulser channels set')

        start_rc()
        app.logger.debug(f'CALIB: ~~~ Run started ~~~')
        time.sleep(8)
        time.sleep(config_dict["pulser_period"])
        pp.run_trig(config_dict["pulser_duration"])
        app.logger.debug(f'CALIB: Pulser finished')
        stop_rc()
        app.logger.debug(f'CALIB: ~~~ Run stopped ~~~')

        run_info.append_subrun_pulser_scan(i, config_led)
        time.sleep(8)

        # if i>2:
        #     break

    time.sleep(10)
    # start_SiPMmoniotoring(logger=app.logger)
    # app.logger.info("CALIB: SiPM bias voltage monitoring restored")

    run_info.write_run_info()
    app.logger.info('CALIB: ~~~~~~~ Run finished, run info written ~~~~~~~')
    
    if file_handler.last_file_path:
        app.logger.debug("Start process last file")
        with FILE_PROCESS_LOCK:
            file_handler.process_file(file_handler.last_file_path)
        app.logger.debug("Done process last file")
        
    return jsonify(None)

# Channel mapping 
@app.route("/api/start_channel_map/", methods=['POST'])
def start_channel_map():
    """
    Perform a channel mapping run sequence. Take some DC data, 6 channels at a time. Scan through all channels.
    Return a json  

    Return:
        channel_map.json
    """
    app.logger.info("CHANNEL MAP: Start channel mapping run")
    # Retrieve the JSON payload
    config_map = request.get_json()
    
    # Safely extract the variable
    if config_map is None:
        return jsonify({"error": "No JSON config received"}), 400
        
    data_folder = config_map.get('data_folder')
    
    if data_folder is None:
        return jsonify({"error": "Missing 'data_folder' in request"}), 400
    else:
        if os.path.exists(data_folder):
            app.logger.info(f"Starting mapping runs. The data output is set to: {data_folder}")
        else:
            return jsonify({"error": f"Data folder path does not exist: {data_folder}"}), 400
    
    # # Retrieve the system config
    # config_dict = Config().parse_yaml()

    with CUR_RUN_LOCK:
        global CUR_RUN
        CUR_RUN = {
            "run": 0,
            "data_stream": "channel_map",
            "run_starting_instance": "lrsctrl"
        }
    
    # Generate the start timestamp string
    start_timestamp = datetime.now().strftime("%Y%m%d_%H%M")

    # 1. First get first sipmpsctrl channel per cable, per TPC
    channel_config = utils.make_mapping_channel_config(app)

    # 2. Check that all expected cables are present for each board
    if not utils.check_channel_config(app, channel_config):
        return jsonify({"error": "Channel configuration is invalid"}), 400

    # 3. Run the channel mapping sequence for each cable, one at a time
    default_voltage =  Config().parse_yaml().get("default_voltage", 1.0)

    for cable_id in sorted(channel_config.keys()):
        app.logger.info(f"Processing Cable ID: {cable_id}")
        
        # Set the bias voltage for the channels associated with this cable ID
        for board_id, board_data in channel_config[cable_id].items():
            set_SiPM_individually(board=board_id, channels=board_data['sipm_bias_chan'], voltages=board_data['sipm_bias'], manage_monitoring=False, logger=app.logger)

        app.logger.info(f"SiPM bias set for all boards for cable ID: {cable_id}")

        # Take data
        app.logger.info("Taking data for 10 seconds...")

        # Set the SiPM bias back to default voltage
        for board_id, board_data in channel_config[cable_id].items():
            default_voltages = [default_voltage] * len(board_data['sipm_bias_chan'])  # Reset to default voltage
            set_SiPM_individually(board=board_id, channels=board_data['sipm_bias_chan'], voltages=default_voltages, manage_monitoring=False, logger=app.logger)

        app.logger.info(f"SiPM bias set back to {default_voltage} V for all boards for cable ID: {cable_id}")

        # Find the data file and store it in the json
        data_file = utils.get_most_recent_file(data_folder)
        channel_config[cable_id]['data_file'] = data_file  # Store the data file path in the cable_data dictionary

    # 4. After all channels are done, create a channel_map.json file with the mapping information and 
    #save it to the data_folder

    # Construct the filename (e.g. 20260727_1107_channel_map.json)
    filename_json = f"{start_timestamp}_channel_map.json"
    with open(os.path.join(data_folder, filename_json), 'w') as f:
        json.dump(channel_config, f, indent=4)
    
    
    return jsonify({"status": "success"}), 200

# Calibration run controls
@app.route("/api/start_test/")
def start_test():
    print("command reached the server")
    
    
    print("command executed, thank for choosing lrsctrl")
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
        #app.logger.debug(CUR_RUN)
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
    directory_to_watch = Config().parse_yaml()["data_path"]
    file_handler = FileHandler()
    watcher_thread = threading.Thread(target=watch_for_new_files, args=(directory_to_watch, file_handler))
    watcher_thread.daemon = True
    watcher_thread.start()
    start_app()
