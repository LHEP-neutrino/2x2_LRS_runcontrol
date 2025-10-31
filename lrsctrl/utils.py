import os
import numpy as np
import pandas as pd
import json
from datetime import datetime


import  lrsctrl.pulser_config_maker
import  lrsctrl.sipmPS_config_maker
from lrscfg.client import Client
from lrscfg.config import Config


# def combine_json_files(input_directory, output_file):
#     combined_data = []

#     # Iterate through each file in the input directory
#     for idx, filename in enumerate(sorted(os.listdir(input_directory))):
#         if filename.endswith(".json"):
#             file_path = os.path.join(input_directory, filename)
#             with open(file_path, "r") as file:
#                 data = json.load(file)
#                 #print(data['data_name'])
#                 data['calib_run'] = data['data_name']
#                 combined_data.append(data)

#     # Write the combined data to the output file
#     with open(output_file, "w") as outfile:
#         json.dump(combined_data, outfile, indent=4)

# def append_json_name(in_json, out_json):
#     # Open the JSON file
#     with open(in_json, 'r') as file:
#         data = json.load(file)

#         data_file = get_most_recent_file(Config().parse_yaml()["calib_data"])
#         data['data_name'] = data_file

#     # Write the updated JSON to the output file
#     with open(out_json, 'w') as file:
#         json.dump(data, file)



def make_calib_files(app):
    app.logger.debug("Start the pulser configs maker")
    pulser_config_files_path = lrsctrl.pulser_config_maker.make(app)
    # print(f"Pulse config done: {pulser_config_files_path}")
    app.logger.debug("Start the sipmPS configs maker")
    sipmPS_configs_files_path = lrsctrl.sipmPS_config_maker.make(app)
    # print(f"sipmPS config done: {sipmPS_configs_files_path}")

    if len(pulser_config_files_path) != len(sipmPS_configs_files_path):
        raise ValueError(f"ERROR: The number of pulser configuration ({len(pulser_config_files_path)}) does not match the number of sipmPS configuration ({len(sipmPS_configs_files_path)})")

    print(f"Number of Configurations written: {len(pulser_config_files_path)}")

    return pulser_config_files_path, sipmPS_configs_files_path

def get_most_recent_file(directory):
    # Get list of files in the directory
    try:
        files = os.listdir(directory)
    except FileNotFoundError as e:
        print(f"Directory {directory} not found.")
        return ""

    # Filter out directories and get file paths
    file_paths = [os.path.join(directory, f) for f in files if os.path.isfile(os.path.join(directory, f))]

    # Sort files by modification time (most recent first)
    file_paths.sort(key=os.path.getmtime, reverse=True)

    # Return the most recent file path
    if file_paths:
        return file_paths[0]
    else:
        return None

# def convert_to_adcs(out_file):
#     # Declaration of variables
#     relevant_adcs = []
#     adc_serials = []
#     local_channels = []
#     final_data = []
#     file_path = out_file

#     # Combine all configuration jsons into a single json
#     combine_json_files(Config().parse_yaml()["pulser_config_path"], Config().parse_yaml()["pulser_config_path"]+"../Merged/"+out_file)

#     # Opens the Merged JSON and finds the pulser settings
#     # Converts those pulser settings into ADC channels
#     # Compiles all that information into a list
#     with open(Config().parse_yaml()["pulser_config_path"]+"../Merged/"+out_file) as f:
#         data = json.load(f)
#         counter = 0
#         for run in data:
#             run_id = (run['calib_run'])
#             print(run_id)
#             print()
#             relevant_adcs = []
#             local_channels = []
#             adc_serials = []
#             for ch_n in run['channels']:
#                 pulser_channel, series, parallel = int(ch_n[2:]), run['channels'][ch_n][0], run['channels'][ch_n][1]
#                 print(pulser_channel, series,parallel)
#                 cl = Client()
#                 filename = cl.get_active_moas()
#                 df = pd.read_csv(Config().parse_yaml()["moas_path"]+filename)
#                 moas_series = df.ser_res_bit
#                 moas_parallel = df.par_res_bit
#                 moas_led = df.led_num
#                 adc_id = df.global_adc_id
#                 adc_ser = df.adc_serial
#                 local_ch = df.adc_0in_chan
#                 for i in range(len(moas_series)):
#                     if int(moas_series[i]) == series and int(moas_parallel[i]) == parallel and int(moas_led[i])-1 == pulser_channel:
#                             #relevant_adcs += [adc_id[i]]
#                             print(run_id, moas_led[i]-1, moas_series[i], moas_parallel[i])
#                             adc_serials += [str(adc_ser[i])]
#                             local_channels += [str(local_ch[i])]
#                             adc_data = {"calib_run":run_id,
#                                         "adc_serials":list(adc_serials),
#                                         "local_channels":list(local_channels)}
#             #print(adc_data)
#             counter += 1
#             if counter < len(data):
#                 final_data.append(adc_data)

#     # Writes it to a file
#     output_file = Config().parse_yaml()["pulser_config_path"]+"../ADCnum/"+out_file
#     with open(output_file, 'w') as json_file:
#         json.dump(final_data, json_file, indent = 4)


class Run_Info:
    def __init__(self, app):
        self.config = Config().parse_yaml()
        self.run_folder = os.path.abspath(self.config["calib_data"])
        
        moas = Client().get_active_moas()
        self.moas = os.path.join(self.config["moas_path"],moas)

        self.subruns = []

        self.logger = app.logger


    def sipmPS_to_adc(self, sipmPS_list):
        """
            Take a list of the form [(modN, sipmPS_chanM), (modX, sipmPS_chanY), ...]
            and convert it to a list of the form [[adcA, adc_chanB], [adcI, adc_chanJ], ...]
        """
        self.logger.debug("Converting PS coordinate to adc coordinate")
        # Load MOAS
        moas = pd.read_csv(self.moas, usecols=["mod_num", "sipm_bias_chan", "adc_nr", "adc_0in_chan"])

        # Set MultiIndex for fast lookup
        moas_indexed = moas.set_index(["mod_num", "sipm_bias_chan"])

        # Use sipmPS_list to find the corresponding adc and adc_chan values
        lookup_results = moas_indexed.reindex(sipmPS_list)

        # Check for missing entries
        if lookup_results.isna().any().any():
            raise ValueError("Some (mod_num, sipm_bias_chan) pairs were not found in moas!")

        # Convert to list of lists [[adc_nr, adc_chan], ...]
        adc_list = lookup_results[["adc_nr", "adc_0in_chan"]].values.tolist()

        return sorted(adc_list, key=lambda x: (x[0], x[1]))
    

    def get_active_chans(self, sipmPS_config_folder):
        self.logger.debug("Get the active channels")
        active_chans = []
        default_voltage = round(self.config["default_voltage"], 2)

        for sipmPS_config_file in os.listdir(sipmPS_config_folder):
            if sipmPS_config_file.endswith(".csv"):
                
                module = int(sipmPS_config_file[3:-4])  # remove first 3 chars and last 4 chars

                sipmPS_config_path = os.path.join(sipmPS_config_folder, sipmPS_config_file)
                sipmPS_config_df = pd.read_csv(sipmPS_config_path, header=None, names=["chan", "V"])

                # Filter rows where value != default_val (allowing for float comparison)
                sipmPS_mask = sipmPS_config_df["V"].round(2) != default_voltage
                sipmPS_active_df = sipmPS_config_df[sipmPS_mask]

                for active_sipmPS_chan in sipmPS_active_df["chan"]:
                    active_chans.append((module, active_sipmPS_chan))                            

        adc_active_chans = self.sipmPS_to_adc(active_chans)

        return adc_active_chans

    def append_subrun(self, subrun_number, pulser_config, sipmPS_config):
        self.logger.debug(f"Append subrun {subrun_number} to the run info")
        subrun_info = {
            "subrun" : subrun_number,
            "data_file" : get_most_recent_file(self.run_folder),
            "pulser_config" : pulser_config,
            "sipmPS_config" : sipmPS_config,
            "active_chans" : self.get_active_chans(sipmPS_config)
        }
        
        self.subruns.append(subrun_info)

        return 0

    def write_run_info(self):
        run_info = {}
        run_info["run_folder"] = self.run_folder
        run_info["moas"] = self.moas
        run_info["subruns"] = self.subruns

        now = datetime.now()
        time_str = now.strftime("%Y%m%d_%H%M%S")
        output_file = f"{time_str}_run_summary.json"
        output_path = os.path.join(self.run_folder, output_file)

        self.logger.debug(f"Writing the run info into {output_path}")

        with open(output_path, "w") as f:
            json.dump(run_info, f, indent=4)
        
        return 0



# if __name__ == "__main__":
#     from datetime import datetime
#     now = datetime.now()
    # dt_string = now.strftime("%Y.%m.%d.%H.%M.%S")
    # out_file = dt_string + '.json'
    # convert_to_adcs(out_file)
