import numpy as np
import json
import pandas as pd
import glob
import os
import shutil

from lrsctrl.config import Config
from lrscfg.client import Client

def map_ledRun_id():
    led_id_map = {}
    folder_ledRun_config = Config().parse_yaml()["pulser_config_path"]
    for cfg_file in glob.glob(os.path.join(folder_ledRun_config, "*.json")): 
        filename = os.path.basename(cfg_file)
        with open(cfg_file) as f:
            data = json.load(f)

        # Step 2: Build led_id mapping
        for ch, (a, b) in data["channels"].items():
            if (a == 0 and b == 100):
                continue
            int_ch = int(ch[2:])
            led_id = f"1{int_ch+1:02d}{a:03d}{b:03d}"

            led_id_map[int(led_id)] = filename

    return led_id_map



def map_ledRun_PSsipm(led_id_map):
    cl = Client()
    filename = cl.get_active_moas()
	# print(filename, Config().parse_yaml()["moas_path"])
    path_moas = os.path.join(Config().parse_yaml()["moas_path"],filename)
    # Load MOAS
    moas = pd.read_csv(path_moas, usecols=["led_group_id_warm","vga_board_num", "sipm_bias_chan", "sipm_bias"])

    ledRun_PSsipm_map = {}

    led_ids = list(led_id_map.keys())

    for i, led_id in enumerate(moas["led_group_id_warm"]):
        
        if led_id in led_ids:
            n_led_run = int(os.path.splitext(led_id_map[led_id])[0])
            
            PS_sipm = [int(moas["vga_board_num"][i]), int(moas["sipm_bias_chan"][i]), float(moas["sipm_bias"][i])]
            ledRun_PSsipm_map.setdefault(n_led_run, []).append(PS_sipm)

    return ledRun_PSsipm_map


def make_sipmPS_config(ledRun_PSsipm_map):
    folder_sipmps_config = Config().parse_yaml()["sipm_config_path"]
    output_path = os.path.join(folder_sipmps_config, "LEDRuns")

    NchanPS = 128
    indices = np.arange(1,NchanPS+1)
    Off_V = int(Config().parse_yaml()["default_voltage"])

    # Delete the output_path folder if it exists
    if os.path.exists(output_path):
        shutil.rmtree(output_path)

    config_folders = []

    for nRun, PSchans in ledRun_PSsipm_map.items():
        print(f"\n {nRun}:  {len(PSchans)}")
        # Create folder for the key
        folder_path = os.path.join(output_path, str(nRun))
        os.makedirs(folder_path, exist_ok=True)  # won't raise error if folder exists
        
        # print(f"Folder created: {folder_path}")
        config_folders.append(folder_path)

        mod0 = np.full(NchanPS, Off_V, dtype=float)
        mod1 = np.full(NchanPS, Off_V, dtype=float)
        mod2 = np.full(NchanPS, Off_V, dtype=float)
        mod3 = np.full(NchanPS, Off_V, dtype=float)
        
        for PSchan in PSchans:
            # print(PSchan)
            if PSchan[0] == 22:
                mod0[PSchan[1]-1]= PSchan[2]
            elif PSchan[0] == 21:
                mod1[PSchan[1]-1]= PSchan[2]
            elif PSchan[0] == 11:
                mod2[PSchan[1]-1]= PSchan[2]
            elif PSchan[0] == 13:
                mod3[PSchan[1]-1]= PSchan[2]

        
        mod0_wChan = np.column_stack((indices, mod0))
        mod1_wChan = np.column_stack((indices, mod1))
        mod2_wChan = np.column_stack((indices, mod2))
        mod3_wChan = np.column_stack((indices, mod3))

        np.savetxt(os.path.join(folder_path,"MOD0.csv"), mod0_wChan, delimiter=",", fmt=["%d", "%.2f"])
        np.savetxt(os.path.join(folder_path,"MOD1.csv"), mod1_wChan, delimiter=",", fmt=["%d", "%.2f"])
        np.savetxt(os.path.join(folder_path,"MOD2.csv"), mod2_wChan, delimiter=",", fmt=["%d", "%.2f"])
        np.savetxt(os.path.join(folder_path,"MOD3.csv"), mod3_wChan, delimiter=",", fmt=["%d", "%.2f"])

    return config_folders 
    


def make():
    ledRun_id_map = map_ledRun_id()
    ledRun_PSsipm_map = map_ledRun_PSsipm(ledRun_id_map)

    # for key in dict(sorted(ledRun_PSsipm_map.items())).keys():
    #     print(f"{key}:\n{dict(sorted(ledRun_PSsipm_map.items()))[key]}")

    sipmPS_configs = make_sipmPS_config(ledRun_PSsipm_map)
    print(f"{len(sipmPS_configs)} SiPM configuration files were made.")

    return sipmPS_configs

if __name__ == "__main__":

   sipmPS_configs = make()
   for config_file in sorted(sipmPS_configs):
       print(config_file)

