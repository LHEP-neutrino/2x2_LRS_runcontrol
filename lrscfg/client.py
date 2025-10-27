import requests
from datetime import datetime
import json
import filecmp, os, glob
import re

import lrscfg.VGA_config_maker as VGA_config_maker
import lrscfg.set_VGAS as set_VGAS
import lrscfg.SIPM_config_maker as SIPM_config_maker
import lrscfg.set_SIPMs as set_SIPMs
from lrscfg.db_handler import DB_Handler
from lrscfg.config import Config
import lrscfg.threshold_handler as threshold_handler


class Client():
    def __init__(self):
        config_settings = Config().parse_yaml()
        self.moas_path = config_settings["moas_path"]
        self.foas_path = config_settings["foas_path"]
        self.latest_moas = self.get_latest_moas()
        self.latest_foas = self.get_latest_foas()
        self.db = DB_Handler()

    def pull_moas(self, tag):
        my_date = datetime.now()

        #pull and save csv
        file_name = my_date.strftime("MOAS_%Y%m%d_%H%M%S.csv")
        file_path = self.moas_path + file_name
        print(file_path)
        moas_url = Config().parse_yaml().get('moas_url')
        pull_command = (
                f"curl -sL '{moas_url}' "
                f"-o '{file_path}'"
        )
        os.system(pull_command)

        if self.latest_moas:
            if filecmp.cmp(file_path,self.moas_path+f"MOAS_{self.latest_moas}.csv"):
                os.remove(file_path)
                print("Current MOAS identical to previous version, no new version created")
                return self.latest_moas
        self.latest_moas = file_name
        print(f"New MOAS created: {file_name}")
        # if not os.path.exists(file_path):
        #     raise FileNotFoundError(f"File not downloaded: {file_path}")

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
        if not version:
            raise ValueError('version must be provided')
        # normalize
        if version.startswith('MOAS_') and version.endswith('.csv'):
            version = version[5:-4]
        elif version.startswith('MOAS_'):
            version = version[5:]
        elif version.endswith('.csv'):
            # maybe 'MOAS_...' or bare filename
            version = os.path.splitext(version)[0]
            if version.startswith('MOAS_'):
                version = version[5:]
        self.db.update_active_configuration(version)

    def pull_foas(self, tag):
        my_date = datetime.now()

        # pull and save csv
        file_name = my_date.strftime("FOAS_%Y%m%d_%H%M%S.csv")
        file_path = self.foas_path + file_name
        # foas_url should be configured in YAML under 'foas_url'
        config_settings = Config().parse_yaml()
        foas_url = config_settings.get('foas_url')
        if not foas_url:
            raise ValueError("foas_url not configured in YAML; cannot pull FOAS file")

        pull_command = f"curl -sL '{foas_url}' -o '{file_path}'"
        os.system(pull_command)

        if self.latest_foas:
            if filecmp.cmp(file_path, self.foas_path + f"FOAS_{self.latest_foas}.csv"):
                os.remove(file_path)
                print("Current FOAS identical to previous version, no new version created")
                return self.latest_foas
        self.latest_foas = file_name
        print(f"New FOAS created: {file_name}")

        # push to db
        self.db.import_foas_configuration(file_path, tag)
        return file_name
    
    def get_latest_foas(self):
        file_type = r"FOAS_*.csv"
        files = glob.glob(self.foas_path + file_type)
        if not files:
            print("No previous FOAS found")
            return None
        latest_file = max(files, key=os.path.getmtime)
        latest_file = os.path.basename(latest_file)
        pattern = r"FOAS_(\d{8}_\d{6})\.csv"
        match = re.search(pattern, latest_file)
        if match:
            return match.group(1)
        else:
            print("No matching FOAS file found!")
            return None

    def get_active_foas(self):
        """Return the active FOAS filename (e.g. 'FOAS_YYYYMMDD_HHMMSS.csv') or None.

        Preference order: DB method if provided, otherwise a small marker file 'FOAS_active.txt'
        inside `foas_path` is used as fallback.
        """

        version = self.db.get_active_foas_configuration()

        if not version:
            print("No active FOAS set")
            return None
        return "FOAS_" + version + ".csv"

    def set_active_foas(self, version):
        """Set the active FOAS version. `version` may be either the bare version string
        (YYYYmmdd_HHMMSS) or the full filename; it will be normalized.
        """
        if not version:
            raise ValueError('version must be provided')
        # normalize
        if version.startswith('FOAS_') and version.endswith('.csv'):
            version = version[5:-4]
        elif version.startswith('FOAS_'):
            version = version[5:]
        elif version.endswith('.csv'):
            # maybe 'FOAS_...' or bare filename
            version = os.path.splitext(version)[0]
            if version.startswith('FOAS_'):
                version = version[5:]

        self.db.update_active_foas_configuration(version)
        
    def activate_moas(self,version):
        if not version:
            version = self.get_latest_moas()
        print("---Make VGA config---")
        VGA_config_maker.make(version)
        print("---Load VGA configs to devices---")
        # print("Virtually setting VGA configs")
        set_VGAS.set_VGA()
        print("---Make SiPM bias config---")
        SIPM_config_maker.make(version)
        print("---Load SiPM bias configs to devices---")
        # print("Virtually setting SiPM configs")
        set_SIPMs.set_SIPM()
        
        print("---Set MOAS as active---")
        self.set_active_moas(version)
        print("---MOAS successfully loaded---")
        
    def activate_foas(self, version):
        """Activate FOAS: load thresholds from FOAS_{version}.csv into ADC and mark as active.

        This will call the threshold handler to write thresholds into the ADC64 JSON
        and then set the FOAS version as active in the DB (or marker file).
        """
        if not version:
            version = self.get_latest_foas()
        print("---Set FOAS thresholds---")
        try:
            threshold_handler.set_thresholds(version, source='FOAS')
        except Exception as e:
            print(f"Error while setting FOAS thresholds: {e}")
            raise

        print("---Set FOAS as active---")
        self.set_active_foas(version)
        print("---FOAS successfully loaded---")
        
    def ramp_down_sipm(self):
        print("---Ramp down SiPMs---")
        set_SIPMs.set_SIPM_zero()
        print("---Ramp finished. Verify in Grafana!!---")