import requests
from lrsctrl.config import Config
import json


class Client():
    def __init__(self):
        server_settings = Config().parse_yaml()
        self.host = server_settings['AppHost']
        self.port = server_settings['AppPort']
        self.url = f'http://{self.host}:{self.port}'

    #Data run controls
    def start_data_run(self,run,data_stream,run_start_instance):
        addr = f'{self.url}/api/start_data_run'
        run_config = {
            "run": run,
            "data_stream": data_stream,
            "run_starting_instance": run_start_instance 
        }
        #run_config_json = json.dumps(run_config, indent=4)
        try:
            requests.post(addr, json=run_config)
        except:
            print(f'Server disconected or script failed!')

    def stop_data_run(self):
        addr = f'{self.url}/api/stop_data_run'
        try:
            requests.get(addr)
        except:
            print(f'Server disconected or script failed!')


    #Calibration run controls
    def start_calib_run(self):
        addr = f'{self.url}/api/start_calib_run/'
        print(addr)
        try:
            requests.get(addr)
        except:
            print(f'Server disconected or script failed!')
    
    # DAQ software controls
    def send_start_adc64(self):
        addr = f'{self.url}/api/start_adc64'
        try:
            requests.get(addr)
        except:
            print(f'Server disconected or script failed!')

    def send_stop_adc64(self):
        addr = f'{self.url}/api/stop_adc64'
        try:
            requests.get(addr)
        except:
            print(f'Server disconected or script failed!')

    def send_start_rc(self):
        addr = f'{self.url}/api/start_rc'
        try:
            requests.get(addr)
        except:
            print(f'Server disconected or script failed!')

    def send_stop_rc(self):
        addr = f'{self.url}/api/stop_rc'
        try:
            requests.get(addr)
        except:
            print(f'Server disconected or script failed!')
