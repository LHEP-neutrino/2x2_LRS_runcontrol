import requests
from lrsctrl.config import Config


class Client():
    def __init__(self):
        server_settings = Config().parse_yaml()
        self.host = server_settings['AppHost']
        self.port = server_settings['AppPort']
        self.url = f'http://{self.host}:{self.port}'

    def send_start_adc64(self):
        addr = f'{self.url}/api/start_adc64'
        try:
            requests.get(addr)
        except:
            print(f'Server disconected! Use CLI command to CLI-server: lrsctrl serve')

    def send_stop_adc64(self):
        addr = f'{self.url}/api/stop_adc64'
        try:
            requests.get(addr)
        except:
            print(f'Server disconected! Use CLI command to CLI-server: lrsctrl serve')

    def send_start_rc(self):
        addr = f'{self.url}/api/start_rc'
        try:
            requests.get(addr)
        except:
            print(f'Server disconected! Use CLI command to CLI-server: lrsctrl serve')

    def send_stop_rc(self):
        addr = f'{self.url}/api/stop_rc'
        try:
            requests.get(addr)
        except:
            print(f'Server disconected! Use CLI command to CLI-server: lrsctrl serve')
