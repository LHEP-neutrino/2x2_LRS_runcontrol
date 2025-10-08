import pandas as pd
import numpy as np
import subprocess
import csv
import sys
import os
import time

from lrscfg.config import Config

WAIT_TIME = 3 # s

def check_supplr_status(server):
    """
        Read the can status of supplr every WAIT_TIME sec until is it free
    """
    cmd_checkSupplr = "supplr can-status"
    while True:
        proc = subprocess.run(
            ['ssh', '-x', f"pi@{server}", cmd_checkSupplr],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        answ = proc.stdout.strip()
        time.sleep(WAIT_TIME)
        if answ != "CAN status: Free":
            print(f"Warning: supplr not ready on {server}. Output: {answ}")
            time.sleep(WAIT_TIME*2)       
        else:
            print(f"supplr ready on {server}")
            return 0

def stop_SiPMmoniotoring():

    print("Stopping SiPM bias voltage monitoring")

    stop_cmd = "screen -S Bias -X quit"
    subprocess.run(['ssh', '-x','pi@acd-sipmpsctrl01.fnal.gov', stop_cmd])
    subprocess.run(['ssh', '-x','pi@acd-sipmpsctrl23.fnal.gov', stop_cmd])
    time.sleep(WAIT_TIME)

    return 0

def start_SiPMmoniotoring():

    print("Starting SiPM bias voltage monitoring")

    start_cmd = "source ~/start_bias_V_in_screen.sh"
    subprocess.run(['ssh', '-x','pi@acd-sipmpsctrl01.fnal.gov', start_cmd])
    subprocess.run(['ssh', '-x','pi@acd-sipmpsctrl23.fnal.gov', start_cmd])
    time.sleep(WAIT_TIME)

    return 0

def set_SIPM(config_folder=None, manage_monitoring=True):
    """
    config_folder: config folder path
    """
    config = Config().parse_yaml()
    if config_folder is None:
        config_folder = os.path.join(config["sipm_config_path"], "tmp/")

    if manage_monitoring == False:
        print("Warning: Monitoring state unchanged. Please check, an active monitoring session may cause network overload.")
    
    N_modules = 4

    if manage_monitoring == True:
        stop_SiPMmoniotoring()


    for n_mod in range(N_modules):
        print(f"Configuring SiPM bias voltage of module {n_mod}")
        config_file = os.path.join(config_folder, f"MOD{n_mod}.csv")
        config_folder_raspi = config["sipm_config_path_raspi"]
        
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
            if n_mod == 2:
                board = 11
            else:
                board = 13

        # Copy the config file on the raspi
        subprocess.run(['scp', config_file, f'pi@{server}:{config_folder_raspi}'])
        time.sleep(WAIT_TIME)

        # Check if supplr ready and capture its output (stdout+stderr) as text
        check_supplr_status(server)

        # Set the SiPM bias voltage
        config_file_raspi = os.path.join(config_folder_raspi, f"MOD{n_mod}.csv")
        cmd_setSiPM = f"supplr set-channel-file --board {board} --file {config_file_raspi}"
        subprocess.run(['ssh', '-x', f"pi@{server}", cmd_setSiPM], check=True)

        print(f"SiPM bias voltage of module {n_mod} configured")

        if n_mod in [0,2]:
            time.sleep(WAIT_TIME)

    if manage_monitoring == True:
            start_SiPMmoniotoring()

    
def set_SIPM_zero():
    print("Ramp down SiPM bias")
    subprocess.run(['ssh', '-x', 'pi@acd-sipmpsctrl01', '.', '~/set0.sh'])
    subprocess.run(['ssh', '-x', 'pi@acd-sipmpsctrl23', '.', '~/set0.sh'])
