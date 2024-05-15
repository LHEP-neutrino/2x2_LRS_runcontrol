import pandas as pd
import numpy as np
import csv
import sys
import os
from datetime import datetime

from lrscfg.client import Client
from lrsctrl.config import Config

def find(Input):
    out = {}
    for elem in Input:
        try:
            out[elem[0]].extend(elem[1:])
        except KeyError:
            out[elem[0]] = list(elem)
    return [tuple(values) for values in out.values()]

def json_writer(file_index, series, parallel):
	import json
	# Data to be written
	dictionary = {#"calib_run": {"run_number": file_index},
	"channels": {
	"ch00": [int(series[0]), int(parallel[0])],
	"ch01": [int(series[1]), int(parallel[1])],
	"ch02": [int(series[2]), int(parallel[2])],
	"ch03": [int(series[3]), int(parallel[3])],
	"ch04": [int(series[4]), int(parallel[4])],
	"ch05": [int(series[5]), int(parallel[5])],
	"ch06": [int(series[6]), int(parallel[6])],
	"ch07": [int(series[7]), int(parallel[7])],
	"ch08": [int(series[8]), int(parallel[8])],
	"ch09": [int(series[9]), int(parallel[9])],
	"ch10": [int(series[10]), int(parallel[10])],
	"ch11": [int(series[11]), int(parallel[11])],
	"ch12": [int(series[12]), int(parallel[12])],
	"ch13": [int(series[13]), int(parallel[13])],
	"ch14": [int(series[14]), int(parallel[14])],
	"ch15": [int(series[15]), int(parallel[15])]
	}

	}
	# Serializing json
	json_object = json.dumps(dictionary)
	# Writing to sample.json
	name = Config().parse_yaml()["pulser_config_path"] + str(file_index) + ".json"
	print(name)
	with open(name, "w") as outfile:
		outfile.write(json_object)

"""
#json_writer()

if len( sys.argv ) > 1:
	file = (sys.argv[1])
	filename = "/home/acd/acdaq/LRS_DAQ/soft/2x2PulserSoft/Pulser/MoAS/"+file
else:
	print("No File Specified")
	print("Defaulting to Most Recent File")
	dir_list = os.listdir("/home/acd/acdaq/LRS_DAQ/soft/2x2PulserSoft/Pulser/MoAS/")
	years = [i[5:9] for i in dir_list]
	months = [str(i[11:12]).zfill(2) for i in dir_list]
	days = [str(i[13:15]).zfill(2) for i in dir_list]
	hours = [str(i[16:18]).zfill(2) for i in dir_list]
	print(hours)
	mins = [str(i[19:21]).zfill(2) for i in dir_list]
	seconds = [str(i[22:24]).zfill(2) for i in dir_list]
	year = max(years)
	month = max([i for i,j in zip(months,years) if j == year])
	day = max([i for i,j,k in zip(days,months,years) if j == month and k == year])
	hour = max([l for l,i,j,k in zip(hours,days,months,years) if i == day and j == month and k == year])
	min = max([m for m,l,i,j,k in zip(mins,hours,days,months,years) if l == hour and i == day and j == month and k == year])
	second = max([n for n,m,l,i,j,k in zip(seconds,mins,hours,days,months,years) if m == min and l == hour and i == day and j == month and k == year])
	file = "MOAS_"+str(year)+"_"+str(month)+"_"+str(day)+"_"+str(hour)+"_"+str(min)+"_"+str(second)+".csv"
	filename = "/home/acd/acdaq/LRS_DAQ/soft/2x2PulserSoft/Pulser/MoAS/"+file

"""
def make():
	cl = Client()
	filename = cl.get_active_moas()
	print(filename, Config().parse_yaml()["moas_path"])
	df = pd.read_csv(Config().parse_yaml()["moas_path"]+filename)

	#df = pd.read_csv(filename)
	#print("Using File: ",filename)

	led_groups = df.led_group_id_warm
	mod_nums = df.mod_num
	tpcs = df.tpc

	configs = []

	TPC_configs = np.empty(shape=(8, 64), dtype='object')

	for tpc, led_group in zip(tpcs, led_groups):
		configs += [[tpc,led_group]]

	unique_data = [list(x) for x in set(tuple(x) for x in configs)]

	settings = (find(sorted(unique_data)))
	pulser_configs = []

	for setting_no in range(max(len(elem) for elem in settings)):
		tmp = []
		for i in range(len(settings)):
			if setting_no < len(settings[i]):
				tmp += [settings[i][setting_no]]
		if setting_no > 0:
			pulser_configs += [tmp]

	pulser_series_resistors = []
	pulser_parallel_resistors = []
	file_indicies = []
	file_index = 0

	for i in pulser_configs:
		file_index += 1
		i = sorted(i)
		series = np.full((16),0)
		parallels = np.full((16),0)
		for j in i:
			led = int(str(j)[-8:-6])
			if led <= 16:
				parallels[led-1] = int(str(j)[-4:-1])
				series[led-1] = int(str(j)[-6:-3])
		series[series > 255] = 0
		parallels[parallels > 255] = 0
		pulser_series_resistors += [series]
		pulser_parallel_resistors += [parallels]
		file_indicies += [str(file_index)]

	for i, ss, ps in zip(file_indicies, pulser_series_resistors, pulser_parallel_resistors):
		json_writer(i, ss, ps)
	return len(pulser_configs)
