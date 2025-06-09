import yaml
from os.path import abspath


REPOSITORY_NAME = f'2x2_LRS_runcontrol'
CONFIG_PATH = f'/{REPOSITORY_NAME}/config.yaml'


class Config:
    def __init__(self):
        self.path = abspath(__file__)
        path_split = self.path.split('/')
        self.app_path = ''
        for word in path_split:
            if word == REPOSITORY_NAME:
                break
            self.app_path += word
            self.app_path += '/'

    def config_path(self):
        self.path_to_config = self.app_path + CONFIG_PATH
        print(self.path_to_config)
        return self.path_to_config

    def parse_yaml(self):
        with open(self.config_path(), "r") as stream:
            self.data = yaml.safe_load(stream)
            return self.data
