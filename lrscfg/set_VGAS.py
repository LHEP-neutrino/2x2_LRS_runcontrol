import pandas as pd
import numpy as np
import subprocess
import csv
import sys
import os

from lrsctrl.config import Config

def set_VGA():
    file_01 = Config().parse_yaml()["vga_config_path"] + "tmp/01.yaml"

    print("Copy VGA configs")
    vga_ctrl_path = Config().parse_yaml()["vga_ctrl_host"] + ':~/gainr_configs/'
    subprocess.run(['scp', file_01, vga_ctrl_path])
    print("Set VGA configs")
    subprocess.run(['ssh',Config().parse_yaml()["vga_ctrl_host"],'.', '~/configure_vga.sh'])
    print("VGA gain set!")
