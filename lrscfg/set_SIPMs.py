import pandas as pd
import numpy as np
import subprocess
import csv
import sys
import os

from lrsctrl.config import Config

def stop_SiPMmoniotoring():

    print("Stopping SiPM bias voltage monitoring")

    stop_cmd = "screen -S Bias -X quit"
    subprocess.run(['ssh','pi@acd-sipmpsctrl01', stop_cmd])
    subprocess.run(['ssh','pi@acd-sipmpsctrl23', stop_cmd])

    return 0

def start_SiPMmoniotoring():

    print("Starting SiPM bias voltage monitoring")

    start_cmd = "source ~/start_bias_V_in_screen.sh"
    subprocess.run(['ssh','pi@acd-sipmpsctrl01', start_cmd])
    subprocess.run(['ssh','pi@acd-sipmpsctrl23', start_cmd])

    return 0

def set_SIPM(config_folder=None, manage_monitoring=True):
    """
    config_folder: config folder path
    """
    if config_folder is None:
        config_folder = os.path.join(Config().parse_yaml()["sipm_config_path"], "tmp/")

    if manage_monitoring == False:
        print("Warning: Monitoring state unchanged. Please check, an active monitoring session may cause network overload.")
    
    N_modules = 4

    if manage_monitoring == True:
        stop_SiPMmoniotoring()


    for n_mod in range(N_modules):
        print(f"Configuring SiPM bias voltage of module {n_mod}")
        config_file = os.path.join(config_folder, f"MOD{n_mod}.csv")
        config_file_raspi = os.path.join(Config().parse_yaml()["sipm_config_path_raspi"], f"MOD{n_mod}.csv")
        
        server = ''
        board = 0
        if n_mod in [0,1]:
            server = 'acd-sipmpsctrl01.fnal.gov'
            if n_mod == 0:
                board = 22
            else:
                board = 21
        elif n_mod in [2,3]:
            server = 'acd-sipmpsctrl23.fnal.gov'
            if n_mod == 0:
                board = 11
            else:
                board = 13
                
        cmd_copy = f"scp {config_file} pi@{server}:{config_file_raspi}"
        subprocess.run(['ssh',f"pi@{server}", 'cmd_setSiPM'])

        cmd_setSiPM = f"supplr set-channel-file --board {board} --file {config_file_raspi}"
        subprocess.run(['ssh',f"pi@{server}", 'cmd_setSiPM'])

        print(f"SiPM bias voltage of module {n_mod} configured")

    if manage_monitoring == True:
            start_SiPMmoniotoring()

    
def set_SIPM_zero():
    print("Ramp down SiPM bias")
    subprocess.run(['ssh','pi@acd-sipmpsctrl01', '.', '~/set0.sh'])
    subprocess.run(['ssh','pi@acd-sipmpsctrl23', '.', '~/set0.sh'])
