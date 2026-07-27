import pandas as pd
import numpy as np
import subprocess
import csv
import sys
import os
import time

from lrscfg.config import Config

WAIT_TIME = 3 # s
WAIT_TRY = 5

BOARD_TO_MODULE = {
    '22': {'module': 0,
           'server': 'acd-sipmpsctrl01.fnal.gov'},
    '21': {'module': 1,
           'server': 'acd-sipmpsctrl01.fnal.gov'},
    '11': {'module': 2,
           'server': 'acd-sipmpsctrl23.fnal.gov'},
    '13': {'module': 3,
           'server': 'acd-sipmpsctrl23.fnal.gov'}
}

MODULE_TO_BOARD = {v['module']: {'board': k, 'server': v['server']} for k, v in BOARD_TO_MODULE.items()}

def restart_supplr(server, logger=None):
    if logger is None:
        print(f"Supplr server on {server} will restart")
    else:
        logger.debug(f"Supplr server on {server} will restart")

    cmd_restartSupplr = "sudo systemctl restart supplr.service"
    # cmd_restartSupplr = "source /home/pi/restart_supplr.sh"
    
    subprocess.run(['ssh', '-x', f"pi@{server}", cmd_restartSupplr], check=True)
    time.sleep(3)

    if logger is None:
        print(f"Supplr server on {server} was restarted")
    else:
        logger.debug(f"Supplr server on {server} was restarted")

    return 0

def check_supplr_status(server, logger=None):
    """
        Read the can status of supplr every WAIT_TIME sec until is it free
    """
    cmd_checkSupplr = "supplr can-status"
    i=0
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
            if logger is None:
                print(f"Warning: supplr not ready on {server} ({i+1}/{WAIT_TRY}). Output: {answ}")
            else:
                logger.debug(f"Warning: supplr not ready on {server}. Output: {answ}")

            if i >= WAIT_TRY-1:
                restart_supplr(server, logger)

            time.sleep(WAIT_TIME*2)       
        else:
            if logger is None:
                print(f"supplr ready on {server}")
            else:
                logger.debug(f"supplr ready on {server}")
            
            return 0

        i += 1

def stop_SiPMmoniotoring(logger=None):
     
    if logger is None:
        print("Stopping SiPM bias voltage monitoring")
    else:   
        logger.debug("Stopping SiPM bias voltage monitoring")

    stop_cmd = "screen -S Bias -X quit"
    subprocess.run(['ssh', '-x','pi@acd-sipmpsctrl01.fnal.gov', stop_cmd])
    subprocess.run(['ssh', '-x','pi@acd-sipmpsctrl23.fnal.gov', stop_cmd])
    time.sleep(WAIT_TIME)

    return 0

def start_SiPMmoniotoring(logger=None):
  
    if logger is None:
        print("Starting SiPM bias voltage monitoring")
    else:   
        logger.debug("Starting SiPM bias voltage monitoring")

    start_cmd = "source ~/start_bias_V_in_screen.sh"
    subprocess.run(['ssh', '-x','pi@acd-sipmpsctrl01.fnal.gov', start_cmd])
    subprocess.run(['ssh', '-x','pi@acd-sipmpsctrl23.fnal.gov', start_cmd])
    time.sleep(WAIT_TIME)

    return 0

def set_SIPM(config_folder=None, manage_monitoring=True, logger=None):
    """
    config_folder: config folder path
    """
    config = Config().parse_yaml()
    if config_folder is None:
        config_folder = os.path.join(config["sipm_config_path"], "tmp/")

    if manage_monitoring == False:
        if logger is None:
            print("Warning: Monitoring state unchanged. Please check, an active monitoring session may cause network overload.")
        else:
            logger.warning("Warning: Monitoring state unchanged. Please check, an active monitoring session may cause network overload.")
    
    # N_modules = 4
    modules = [0, 2, 1, 3] # Alternate supplr to minimize the chance of error

    if manage_monitoring == True:
        stop_SiPMmoniotoring(logger=logger)


    # for n_mod in range(N_modules):
    for n_mod in modules:

        if logger is None:
            print(f"Configuring SiPM bias voltage of module {n_mod}")
        else:
            logger.debug(f"Configuring SiPM bias voltage of module {n_mod}")

        config_file = os.path.join(config_folder, f"MOD{n_mod}.csv")
        config_folder_raspi = config["sipm_config_path_raspi"]

        # Copy the config file on the raspi
        
        subprocess.run(['scp', config_file, f'pi@{MODULE_TO_BOARD[n_mod]["server"]}:{config_folder_raspi}'])
        if logger is None:
            print(f"Config files copied to {MODULE_TO_BOARD[n_mod]['server']}:{config_folder_raspi}")
        else:
            logger.debug(f"Config files copied to {MODULE_TO_BOARD[n_mod]['server']}:{config_folder_raspi}")
        time.sleep(WAIT_TIME)

        # Check if supplr ready and capture its output (stdout+stderr) as text
        check_supplr_status(MODULE_TO_BOARD[n_mod]['server'], logger=logger)

        # Set the SiPM bias voltage
        config_file_raspi = os.path.join(config_folder_raspi, f"MOD{n_mod}.csv")
        cmd_setSiPM = f"supplr set-channel-file --board {MODULE_TO_BOARD[n_mod]['board']} --file {config_file_raspi}"
        subprocess.run(['ssh', '-x', f"pi@{MODULE_TO_BOARD[n_mod]['server']}", cmd_setSiPM], check=True)

        if logger is None:
            print(f"SiPM bias voltage of module {n_mod} configured")
        else:
            logger.debug(f"SiPM bias voltage of module {n_mod} configured")

        # if n_mod in [0,2]:     # not necessary anymore, the modules alternate now
        #     time.sleep(WAIT_TIME)

    if manage_monitoring == True:
            start_SiPMmoniotoring(logger=logger)

def set_SiPM_individually(board, channels, voltages, manage_monitoring=True, logger=None):
    """
    Set the SiPM bias voltage for individual channels.
    Args:
        board (int): The board number
        channels (list): list of channels to set
        voltages (list): list of voltages to set
        manage_monitoring (bool): If True, stop and start monitoring during the operation
        logger: logger object for logging messages
    """
    if len(channels) != len(voltages):
        raise ValueError("Channels and voltages lists must have the same length")
    
    if manage_monitoring == True:
        stop_SiPMmoniotoring(logger=logger)

    # Construct the list of commands to set the SiPM bias voltage for each channel
    commands = [f"supplr set-channel --board {board} --channel {channel} --voltage {voltage}"
                for channel, voltage in zip(channels, voltages)]
    script = "\n".join(commands)

    print(f"cmd script:\n{script}")

    # Execute the commands on the appropriate server
    # server = BOARD_TO_MODULE[str(board)]['server']
    # subprocess.run(['ssh', '-x', server, 'bash', '-s'],
    #                 input=script,
    #                 text=True,
    #                 check=True)
    
    if logger is None:
        print(f"SiPM bias voltage of channels {channels} set to {voltages} V")
    else:
        logger.debug(f"SiPM bias voltage of channels {channels} set to {voltages} V")

    if manage_monitoring == True:
        start_SiPMmoniotoring(logger=logger)
    
def set_SIPM_default():
    print("Ramp down SiPM bias")
    subprocess.run(['ssh', '-x', 'pi@acd-sipmpsctrl01', '.', '~/set_default.sh'])
    subprocess.run(['ssh', '-x', 'pi@acd-sipmpsctrl23', '.', '~/set_default.sh'])
