import requests
from lrsctrl.config import Config
from lrscfg.db_handler import DB_Handler
from datetime import datetime
import json
import filecmp, os, glob
import re

import lrscfg.VGA_config_maker as VGA_config_maker
import lrscfg.set_VGAS as set_VGAS
import lrscfg.SIPM_config_maker as SIPM_config_maker
import lrscfg.set_SIPMs as set_SIPMs


class Client():
    def __init__(self):
        config_settings = Config().parse_yaml()
        self.moas_path = config_settings["moas_path"]
        self.latest_moas = self.get_latest_moas()
        self.db = DB_Handler()

    def pull_moas(self, tag):
        my_date = datetime.now()

        #pull and save csv
        file_name = my_date.strftime("MOAS_%Y%m%d_%H%M%S.csv")
        file_path = self.moas_path + file_name
        print(file_path)
        pull_command = "wget 'https://docs.google.com/spreadsheets/d/13CcIy80dR0nSdZkhVfw3O8aI-YYRBjdlX6SshXjmRLM/export?format=csv&gid=1062843003' -O '" + file_path + "' &> /dev/null"
        os.system(pull_command)
        if self.latest_moas:
            if filecmp.cmp(file_path,self.moas_path+f"MOAS_{self.latest_moas}.csv"):
                os.remove(file_path)
                print("Current MOAS identical to previous version, no new version created")
                return self.latest_moas
        self.latest_moas = file_name
        print(f"New MOAS created: {file_name}")

        #push to db
        self.db.import_configuration(file_path, tag)
        return file_name
    
    def get_latest_moas(self):
        file_type = r"MOAS_*.csv"
        files = glob.glob(self.moas_path + file_type)
        if not files:
            print("No previous MOAS found")
            return None
        latest_file = max(files, key=os.path.getmtime)
        latest_file = os.path.basename(latest_file)
        pattern = r"MOAS_(\d{8}_\d{6})\.csv"
        match = re.search(pattern, latest_file)
        if match:
            return match.group(1)
        else:
            print("No matching file found!")
            return None

    def get_active_moas(self):
        version = self.db.get_active_configuration()
        if not version:
            print("No active MOAS set")
            return None
        return "MOAS_" + version + ".csv"

    def set_active_moas(self, version):
        self.db.update_active_configuration(version)
        
    def activate_moas(self,version):
        if not version:
            version = self.get_latest_moas()
        print("---Make VGA config---")
        VGA_config_maker.make(version)
        print("---Load VGA configs to devices---")
        set_VGAS.set_VGA()
        print("---Make SiPM bias config---")
        SIPM_config_maker.make(version)
        print("---Load SiPM bias configs to devices---")
        set_SIPMs.set_SIPM()
        
        print("---Set MOAS as active---")
        self.set_active_moas(version)
        print("---MOAS successfully loaded---")
        