import pandas as pd
import numpy as np
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

def csv_maker(filename, list1, list2):
    with open(filename, mode='w', newline='') as file:
        writer = csv.writer(file)
        for item1, item2 in zip(list1, list2):
            writer.writerow([item1, item2])

def make(moas_version):
    #filename = cl.get_active_moas()
    filename = f"MOAS_{moas_version}.csv"
    df = pd.read_csv(Config().parse_yaml()["moas_path"]+filename)

    tpc0_sipm_chan = list(df.sipm_bias_chan[df.tpc==0])
    tpc1_sipm_chan = list(df.sipm_bias_chan[df.tpc==1])

    tpc0_bias = list(df.sipm_bias[df.tpc==0])
    tpc1_bias = list(df.sipm_bias[df.tpc==1])

    print("Write config for sipmpsctrl01")
    path = Config().parse_yaml()["sipm_config_path"]
    file = path+"tpc0_"+filename[0:-4]+".csv"
    csv_maker(file, tpc0_sipm_chan, tpc0_bias)
    file = path+"tpc1_"+filename[0:-4]+".csv"
    csv_maker(file, tpc1_sipm_chan, tpc1_bias)

    print("Write config for sipmpsctrl01")
    path = Config().parse_yaml()["sipm_config_path"] + 'tmp/'
    file = path+"tpc0.csv"
    csv_maker(file, tpc0_sipm_chan, tpc0_bias)
    file = path+"tpc1.csv"
    csv_maker(file, tpc1_sipm_chan, tpc1_bias)

