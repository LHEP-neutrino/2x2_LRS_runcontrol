import pandas as pd
import numpy as np
import subprocess
import csv
import sys
import os

from lrsctrl.config import Config

def set_VGA():
    file_01 = Config().parse_yaml()["vga_config_path"] + "tmp/01.yaml"
    file_23 = Config().parse_yaml()["vga_config_path"] + "tmp/23.yaml"

    print("Copy VGA gain configs")
    subprocess.run(['scp', file_01, 'pi@acd-vgactrl01:~/soft/gainr/'])
    subprocess.run(['scp', file_23, 'pi@acd-vgactrl23:~/soft/gainr/'])
    print("Set VGA gain configs")
    subprocess.run(['ssh','pi@acd-vgactrl01', '.', '~/configure.sh'])
    subprocess.run(['ssh','pi@acd-vgactrl23', '.', '~/configure.sh'])
    print("VGA gain set!")
