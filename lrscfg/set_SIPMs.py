import pandas as pd
import numpy as np
import subprocess
import csv
import sys
import os

from lrsctrl.config import Config

def set_SIPM():
    #subprocess.run("python3 SIPM_config_maker.py")
    file_0 = Config().parse_yaml()["sipm_config_path"] + "tmp/MOD0.csv"
    file_1 = Config().parse_yaml()["sipm_config_path"] + "tmp/MOD1.csv"
    file_2 = Config().parse_yaml()["sipm_config_path"] + "tmp/MOD2.csv"
    file_3 = Config().parse_yaml()["sipm_config_path"] + "tmp/MOD3.csv"
    subprocess.run(['ssh','pi@acd-sipmpsctrl01','screen -S foo -X quit'])
    print("Copy SIPM configs")
    subprocess.run(['scp', file_0, file_1, 'pi@acd-sipmpsctrl01:~/supplr/Configuration_CSVs/'])
    subprocess.run(['scp', file_2, file_3, 'pi@acd-sipmpsctrl23:~/supplr/Configuration_CSVs/'])
    print("Set SIPM configs")
    subprocess.run(['ssh','pi@acd-sipmpsctrl01', '.', '~/configure.sh'])
    subprocess.run(['ssh','pi@acd-sipmpsctrl23', '.', '~/configure.sh'])

#suprocess.run(['screen', '-x', 'LRS_calib_runs'])
