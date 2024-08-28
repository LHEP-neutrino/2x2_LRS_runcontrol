import pandas as pd
import numpy as np
import yaml
import csv
import sys
import os

from lrsctrl.config import Config

def find(Input):
    out = {}
    for elem in Input:
        try:
            out[elem[0]].extend(elem[1:])
        except KeyError:
            out[elem[0]] = list(elem)
    return [tuple(values) for values in out.values()]

def json_writer(file_index, dBs, type):
    import json
    # Data to be written
    data = {
        "endpoint": 'http://localhost:5000',

        "channels":
        {0: int(dBs[0]),
        1: int(dBs[1]),
        2: int(dBs[2]),
        3: int(dBs[3]),
        4: int(dBs[4]),
        5: int(dBs[5]),
        6: int(dBs[6]),
        7: int(dBs[7])}
    }

    yaml_file = Config().parse_yaml()["vga_config_path"] + str(file_index) + ".yaml"
    with open(yaml_file, "w") as outfile:
        yaml.dump(data, outfile, default_flow_style=False, sort_keys=False)
        print(f"Wrote {yaml_file}")

    yaml_file = Config().parse_yaml()["vga_config_path"] +"tmp/" + type + ".yaml"
    with open(yaml_file, "w") as outfile:
        yaml.dump(data, outfile, default_flow_style=False, sort_keys=False)
        print(f"Wrote {yaml_file}")

def make(moas_version):
    #filename = cl.get_active_moas()
    #print(filename, Config().parse_yaml()["moas_path"])
    filename = f"MOAS_{moas_version}.csv"
    df = pd.read_csv(Config().parse_yaml()["moas_path"]+filename)

    vga_pos = list(df.vga_pos)
    first_vga_pos = vga_pos[0:int(len(vga_pos)/2)]
    last_vga_pos = vga_pos[int(len(vga_pos)/2):]

    vga_gain = list(df.vga_gain)
    tpcs = df.tpc

    mod_first_vga_pos = [first_vga_pos[i] for i in range(len(first_vga_pos)) if i == 0 or first_vga_pos[i] != first_vga_pos[i-1]]
    mod_last_vga_pos = [last_vga_pos[i] for i in range(len(last_vga_pos)) if i == 0 or last_vga_pos[i] != last_vga_pos[i-1]]

    first_gains = [vga_gain[vga_pos.index(i)] for i in mod_first_vga_pos]
    last_gains = [vga_gain[vga_pos.index(i)+int(len(vga_pos)/2)] for i in mod_last_vga_pos]

    json_writer("MOD01_gains_"+str(filename[:-4]), first_gains, "01")
    json_writer("MOD23_gains_"+str(filename[:-4]), last_gains, "23")
