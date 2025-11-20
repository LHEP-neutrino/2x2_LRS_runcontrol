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
    NchanPS = 128
    indices = np.arange(1,NchanPS+1)
    Off_V = int(Config().parse_yaml()["default_voltage"])

    mod0 = np.full(NchanPS, Off_V, dtype=float)
    mod1 = np.full(NchanPS, Off_V, dtype=float)
    mod2 = np.full(NchanPS, Off_V, dtype=float)
    mod3 = np.full(NchanPS, Off_V, dtype=float)

    filename = f"MOAS_{moas_version}.csv"
    path_moas = os.path.join(Config().parse_yaml()["moas_path"],filename)
    # Load MOAS
    moas = pd.read_csv(path_moas, usecols=["vga_board_num", "sipm_bias_chan", "sipm_bias"])


    sipm_bias_chan = moas["sipm_bias_chan"]
    vga_board_num = moas["vga_board_num"]
    sipms_bias = moas["sipm_bias"]
    # adc_chans = moas["adc_0in_chan"]

    for sipmPS_board, sipmPS_chan, sipm_bias in zip(vga_board_num, sipm_bias_chan, sipms_bias):
        if sipmPS_board == 22:
            mod0[sipmPS_chan-1]= sipm_bias
        elif sipmPS_board == 21:
            mod1[sipmPS_chan-1]= sipm_bias
        elif sipmPS_board == 11:
            mod2[sipmPS_chan-1]= sipm_bias
        elif sipmPS_board == 13:
            mod3[sipmPS_chan-1]= sipm_bias
        else:
            print("WARNING: no correspondance between sipmPS {sipmPS_chan}, board {sipmPS_board} and an adc channel.")

    mod0_wChan = np.column_stack((indices, mod0))
    mod1_wChan = np.column_stack((indices, mod1))
    mod2_wChan = np.column_stack((indices, mod2))
    mod3_wChan = np.column_stack((indices, mod3))

    folder_path = Config().parse_yaml()["sipm_config_path"]

    np.savetxt(os.path.join(folder_path,f"MOD0_{filename[0:-4]}.csv"), mod0_wChan, delimiter=",", fmt=["%d", "%.2f"])
    np.savetxt(os.path.join(folder_path,f"MOD1_{filename[0:-4]}.csv"), mod1_wChan, delimiter=",", fmt=["%d", "%.2f"])
    np.savetxt(os.path.join(folder_path,f"MOD2_{filename[0:-4]}.csv"), mod2_wChan, delimiter=",", fmt=["%d", "%.2f"])
    np.savetxt(os.path.join(folder_path,f"MOD3_{filename[0:-4]}.csv"), mod3_wChan, delimiter=",", fmt=["%d", "%.2f"])

    folder_path = os.path.join(Config().parse_yaml()["sipm_config_path"], 'tmp/')

    np.savetxt(os.path.join(folder_path,"MOD0.csv"), mod0_wChan, delimiter=",", fmt=["%d", "%.2f"])
    np.savetxt(os.path.join(folder_path,"MOD1.csv"), mod1_wChan, delimiter=",", fmt=["%d", "%.2f"])
    np.savetxt(os.path.join(folder_path,"MOD2.csv"), mod2_wChan, delimiter=",", fmt=["%d", "%.2f"])
    np.savetxt(os.path.join(folder_path,"MOD3.csv"), mod3_wChan, delimiter=",", fmt=["%d", "%.2f"])


    # mod0_sipm_chan = sipm_bias_chan[0:int(len(sipm_bias_chan)/4)]
    # mod1_sipm_chan = sipm_bias_chan[int(len(sipm_bias_chan)/4):int(2*len(sipm_bias_chan)/4)]
    # mod2_sipm_chan = sipm_bias_chan[int(2*len(sipm_bias_chan)/4):int(3*len(sipm_bias_chan)/4)]
    # mod3_sipm_chan = sipm_bias_chan[int(3*len(sipm_bias_chan)/4):]

    # sipm_bias = list(moas.sipm_bias)

    # mod0_bias = [sipm_bias[sipm_bias_chan.index(i)] for i in mod0_sipm_chan]
    # mod1_bias = [sipm_bias[sipm_bias_chan.index(i)+int(len(sipm_bias_chan)/4)] for i in mod1_sipm_chan]
    # mod2_bias = [sipm_bias[sipm_bias_chan.index(i)+int(2*len(sipm_bias_chan)/4)] for i in mod2_sipm_chan]
    # mod3_bias = [sipm_bias[sipm_bias_chan.index(i)+int(3*len(sipm_bias_chan)/4)] for i in mod3_sipm_chan]

    # print("Write config for sipmpsctrl01")
    # path = Config().parse_yaml()["sipm_config_path"]
    # file = path+"MOD0_"+filename[0:-4]+".csv"
    # csv_maker(file, mod0_sipm_chan, mod0_bias)
    # file = path+"MOD1_"+filename[0:-4]+".csv"
    # csv_maker(file, mod1_sipm_chan, mod1_bias)
    # file = path+"MOD2_"+filename[0:-4]+".csv"
    # csv_maker(file, mod2_sipm_chan, mod2_bias)
    # file = path+"MOD3_"+filename[0:-4]+".csv"
    # csv_maker(file, mod3_sipm_chan, mod3_bias)

    # print("Write config for sipmpsctrl01")
    # path = Config().parse_yaml()["sipm_config_path"] + 'tmp/'
    # file = path+"MOD0.csv"
    # csv_maker(file, mod0_sipm_chan, mod0_bias)
    # file = path+"MOD1.csv"
    # csv_maker(file, mod1_sipm_chan, mod1_bias)
    # file = path+"MOD2.csv"
    # csv_maker(file, mod2_sipm_chan, mod2_bias)
    # file = path+"MOD3.csv"
    # csv_maker(file, mod3_sipm_chan, mod3_bias)

