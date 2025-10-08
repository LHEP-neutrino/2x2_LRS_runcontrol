import pandas as pd
import numpy as np
import os
from datetime import datetime
import json
import shutil

from lrscfg.client import Client
from lrscfg.config import Config

def regroup_tpc(Input):
    out = {}
    for elem in Input:
        try:
            out[elem[0]].extend(elem[1:])
        except KeyError:
            out[elem[0]] = list(elem)
    return [tuple(values) for values in out.values()]

def json_writer(config_file_path, series, parallel):
	
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
	print(config_file_path)
	with open(config_file_path, "w") as output_file:
		output_file.write(json_object)

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



def get_led_params(led_id):
	chan = led_id // 1_000_000 % 100	# second and third digits
	s = (led_id // 1_000) % 1_000  		# middle 3 digits
	p = led_id % 1_000        			# last 3 digits

	return chan, s, p

def check_valid_led_id(led_id):
	chan, s, p = get_led_params(led_id)

	# Check that the id is valid 
	return chan <= 16 and  s <= 255 and p <= 255


def make():
	moas_name = Client().get_active_moas()
	moas_path = os.path.join(Config().parse_yaml()["moas_path"], moas_name)
	print(f" MOAS: {moas_name}")
	moas_df = pd.read_csv(moas_path, usecols=["led_group_id_warm","tpc"])

	pulser_config_folder = Config().parse_yaml()["pulser_config_path"]

	# Delete the output_path folder if it exists and create it again
	if os.path.exists(pulser_config_folder):
		shutil.rmtree(pulser_config_folder)
	os.makedirs(pulser_config_folder, mode=0o755)
	
	led_groups = moas_df["led_group_id_warm"]
	tpcs = moas_df["tpc"]

	chans_config = []

	for tpc, led_group in zip(tpcs, led_groups):
		if check_valid_led_id(led_group):
			chans_config += [(tpc,led_group)]

	# print(f"configs ({len(chans_config)}): {chans_config}")

	# print(f"configs ({len(set(chans_config))}): {set(chans_config)}")
	# return 0

	unique_pulser_config = [list(chan_config) for chan_config in set(chans_config)]

	print(f"unique_pulser_config_data ({len(unique_pulser_config)}): {unique_pulser_config}")
	# return 0

	
	settings = regroup_tpc(sorted(unique_pulser_config))

	# for i in range(len(settings)):
	# 	print(f"settings {i} ({len(settings[i])}): {settings[i]}")
	# return 0
	pulser_configs = []

	for setting_no in range(max(len(elem) for elem in settings)):
		print(f"\nSetting_no: {setting_no}")
		
		print(f"{max(len(elem) for elem in settings)}")
		tmp = []
		for i in range(len(settings)):
			if setting_no < len(settings[i]):
				tmp += [settings[i][setting_no]]
		if setting_no > 0:
			pulser_configs += [sorted(tmp)]
			# print(f"\nsetting_no: {setting_no}, tmp ({len(tmp)}): {sorted(tmp)}")
			# input("Press Enter to continue...")


	pulser_series_configs = []
	pulser_parallels_configs = []
	config_files_path = []

	for i_config, config in enumerate(pulser_configs):
		
		series = np.full((16),0)
		parallels = np.full((16),100)

		for led_id in config:
			if check_valid_led_id(led_id):
				led, s, p = get_led_params(led_id)
				parallels[led-1] = p
				series[led-1] = s

		pulser_series_configs += [series]
		pulser_parallels_configs += [parallels]
		output_path = os.path.join(pulser_config_folder, f"{i_config:02d}.json")
		# print(output_path)
		config_files_path += [output_path]

	for config_file_path, pulser_series_config, p_parallels_config in zip(config_files_path, pulser_series_configs, pulser_parallels_configs):
		json_writer(config_file_path, pulser_series_config, p_parallels_config)
	return config_files_path

if __name__ == "__main__":
	# print(check_valid_led_id(119234123))
	make()
