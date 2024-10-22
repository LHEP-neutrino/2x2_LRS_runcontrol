import pandas as pd
import numpy as np
import subprocess
import csv
import sys
import os

from lrsctrl.config import Config

def set_SIPM():
    sipm_config_path = Config().parse_yaml()["sipm_config_path"]
    sipm_ctrl_host = Config().parse_yaml()["sipm_ctrl_host"]
    file_0 = sipm_config_path + "tmp/tpc0.csv"
    file_1 = sipm_config_path + "tmp/tpc1.csv"
    #subprocess.run(['ssh','pi@acd-sipmpsctrl01','screen -S foo -X quit'])
    print("Copy SIPM configs")
    sipm_ctrl_path = sipm_ctrl_host + ':~/supplr_configs/'
    subprocess.run(['scp', file_0, file_1, sipm_ctrl_path])
    print("Set SIPM configs")
    subprocess.run(['ssh',sipm_ctrl_host, '.', '~/configure_sipm.sh'])
    
def set_SIPM_zero():
    print("Ramp down SiPM bias")
    sipm_ctrl_host = Config().parse_yaml()["sipm_ctrl_host"]
    subprocess.run(['ssh',sipm_ctrl_host, '.', '~/set0.sh'])