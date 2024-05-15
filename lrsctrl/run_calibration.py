import os
import numpy as np
import pandas as pd
import  lrsctrl.pulser_config_maker

from lrscfg.client import Client
from lrsctrl.config import Config
cl = Client()

import json

def combine_json_files(input_directory, output_file):
    combined_data = []

    # Iterate through each file in the input directory
    for idx, filename in enumerate(sorted(os.listdir(input_directory))):
        if filename.endswith(".json"):
            file_path = os.path.join(input_directory, filename)
            with open(file_path, "r") as file:
                data = json.load(file)
                print(data['data_name'])
                data['calib_run'] = data['data_name']
                combined_data.append(data)

    # Write the combined data to the output file
    with open(output_file, "w") as outfile:
        json.dump(combined_data, outfile, indent=4)

def append_json_name(in_json, out_json):
	# Open the JSON file
	with open(in_json, 'r') as file:
	    data = json.load(file)

	data_file = get_most_recent_file(Config().parse_yaml()["calib_data"])
	data['data_name'] = data_file

	# Close the file
	with open(out_json, 'w') as file:
	    json.dump(data, file)

def run_calibration():
    commands = []
    base = Config().parse_yaml()["pulser_config_path"]
    os.system('rm /data/LRS_det_config/pulser_config/Config/*.json')
    number_of_configs = lrsctrl.pulser_config_maker.make()
    print("Number of Configurations: ",number_of_configs)
    for i in range(number_of_configs):
        filename = base + str(i+1) + ".json"
        adjust_command = filename
        commands += [adjust_command]
    return commands

def get_most_recent_file(directory):
    # Get list of files in the directory
    files = os.listdir(directory)

    # Filter out directories and get file paths
    file_paths = [os.path.join(directory, f) for f in files if os.path.isfile(os.path.join(directory, f))]

    # Sort files by modification time (most recent first)
    file_paths.sort(key=os.path.getmtime, reverse=True)

    # Return the most recent file path
    if file_paths:
        return file_paths[0]
    else:
        return None

def convert_to_adcs(out_file):
    # Declaration of variables
    relevant_adcs = []
    adc_serials = []
    local_channels = []
    final_data = []
    file_path = out_file

    # Combine all configuration jsons into a single json
    combine_json_files(Config().parse_yaml()["pulser_config_path"], Config().parse_yaml()["pulser_config_path"]+"../Merged/"+out_file)

    # Opens the Merged JSON and finds the pulser settings
    # Converts those pulser settings into ADC channels
    # Compiles all that information into a list
    with open(Config().parse_yaml()["pulser_config_path"]+"../Merged/"+out_file) as f:
        data = json.load(f)
        for run in data:
            run_id = (run['calib_run'])
            print(run_id)
            print()
            relevant_adcs = []
            local_channels = []
            adc_serials = []
            for ch_n in run['channels']:
                pulser_channel, series, parallel = int(ch_n[2:]), run['channels'][ch_n][0], run['channels'][ch_n][1]
                cl = Client()
                filename = cl.get_active_moas()
                df = pd.read_csv(Config().parse_yaml()["moas_path"]+filename)
                moas_series = df.ser_res_bit
                moas_parallel = df.par_res_bit
                moas_led = df.led_num
                adc_id = df.global_adc_id
                adc_ser = df.adc_serial
                local_ch = df.adc_0in_chan
                for i in range(len(moas_series)):
                    if int(moas_series[i]) == series and int(moas_parallel[i]) == parallel:# and int(moas_led[i]) == pulser_channel:
                            #relevant_adcs += [adc_id[i]]
                            adc_serials += [str(adc_ser[i])]
                            local_channels += [str(local_ch[i])]
                            adc_data = {"calib_run":run_id,
                                        "adc_serials":list(adc_serials),
                                        "local_channels":list(local_channels)}
            final_data.append(adc_data)

    # Writes it to a file
    output_file = Config().parse_yaml()["pulser_config_path"]+"../ADCnum/"+out_file
    with open(output_file, 'w') as json_file:
        json.dump(final_data, json_file, indent = 4)

if __name__ == "__main__":
    from datetime import datetime
    now = datetime.now()
    dt_string = now.strftime("%Y.%m.%d.%H.%M.%S")
    out_file = dt_string + '.json'
    convert_to_adcs(out_file)
