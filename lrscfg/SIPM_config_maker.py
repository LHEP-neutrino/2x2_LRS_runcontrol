import pandas as pd
import numpy as np
import csv
import sys
import os

from lrscfg.config import Config

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

    sipm_bias_chan = list(df.sipm_bias_chan)

    mod0_sipm_chan = sipm_bias_chan[0:int(len(sipm_bias_chan)/4)]
    mod1_sipm_chan = sipm_bias_chan[int(len(sipm_bias_chan)/4):int(2*len(sipm_bias_chan)/4)]
    mod2_sipm_chan = sipm_bias_chan[int(2*len(sipm_bias_chan)/4):int(3*len(sipm_bias_chan)/4)]
    mod3_sipm_chan = sipm_bias_chan[int(3*len(sipm_bias_chan)/4):]

    sipm_bias = list(df.sipm_bias)

    mod0_bias = [sipm_bias[sipm_bias_chan.index(i)] for i in mod0_sipm_chan]
    mod1_bias = [sipm_bias[sipm_bias_chan.index(i)+int(len(sipm_bias_chan)/4)] for i in mod1_sipm_chan]
    mod2_bias = [sipm_bias[sipm_bias_chan.index(i)+int(2*len(sipm_bias_chan)/4)] for i in mod2_sipm_chan]
    mod3_bias = [sipm_bias[sipm_bias_chan.index(i)+int(3*len(sipm_bias_chan)/4)] for i in mod3_sipm_chan]

    print("Write config for sipmpsctrl01")
    path = Config().parse_yaml()["sipm_config_path"]
    file = path+"MOD0_"+filename[0:-4]+".csv"
    csv_maker(file, mod0_sipm_chan, mod0_bias)
    file = path+"MOD1_"+filename[0:-4]+".csv"
    csv_maker(file, mod1_sipm_chan, mod1_bias)
    file = path+"MOD2_"+filename[0:-4]+".csv"
    csv_maker(file, mod2_sipm_chan, mod2_bias)
    file = path+"MOD3_"+filename[0:-4]+".csv"
    csv_maker(file, mod3_sipm_chan, mod3_bias)

    print("Write config for sipmpsctrl01")
    path = Config().parse_yaml()["sipm_config_path"] + 'tmp/'
    file = path+"MOD0.csv"
    csv_maker(file, mod0_sipm_chan, mod0_bias)
    file = path+"MOD1.csv"
    csv_maker(file, mod1_sipm_chan, mod1_bias)
    file = path+"MOD2.csv"
    csv_maker(file, mod2_sipm_chan, mod2_bias)
    file = path+"MOD3.csv"
    csv_maker(file, mod3_sipm_chan, mod3_bias)

