import pandas as pd
import numpy as np
import csv
import os
import json
from pathlib import Path
from collections import defaultdict

from lrscfg.config import Config

def get_active_reg_config(cfg):
    
    afi_base = cfg.get('afi_config_path')
    if not afi_base:
        raise KeyError("'afi_config_path' not found in configuration")

    afi_base = Path(os.path.expanduser(afi_base))
    if not afi_base.is_absolute():
        afi_base = Path(Config().app_path) / afi_base
    afi_base = afi_base.resolve()

    if not afi_base.exists() or not afi_base.is_dir():
        raise FileNotFoundError(f"AFI config base directory not found: {afi_base}")

    cur_env_path = cfg.get('cur_daq_env_path')
    if not cur_env_path:
        raise KeyError("'cur_daq_env_path' not found in configuration")

    cur_env_path = Path(os.path.expanduser(cur_env_path))
    if not cur_env_path.is_absolute():
        cur_env_path = Path(Config().app_path) / cur_env_path
    cur_env_path = cur_env_path.resolve()

    if not cur_env_path.exists():
        raise FileNotFoundError(f"cur_daq_env_path does not exist: {cur_env_path}")

    with open(cur_env_path, 'r') as f:
        env_name = f.read().strip()

    if not env_name:
        raise ValueError(f"No environment name found in {cur_env_path}")
    
    reg_config_path = afi_base / 'Adc64' / f"{env_name}_reg" / 'default.json'
    
    return Path(reg_config_path)

def get_enabled_channels(version, cfg=None):
    """Return (adc_serial, channel, enabled_flag).
    Load the enabled channel configuration from the MOAS.
    """
    cfg = Config().parse_yaml() if cfg is None else cfg

    base = cfg.get('moas_path')
    if not base:
        raise ValueError("moas_path not configured in YAML; cannot locate MOAS file")

    filename = f"MOAS_{version}.csv"
    moas_file = os.path.join(base, filename)
    if not os.path.exists(moas_file):
        raise FileNotFoundError(f"MOAS file not found: {moas_file}")

    df = pd.read_csv(moas_file)
    # Expect columns 'adc_serial', 'adc_0in_chan' and 'ch_enabled'
    required = ('adc_serial', 'adc_0in_chan', 'ch_enabled')
    for col in required:
        if col not in df.columns:
            raise ValueError(f'MOAS CSV must contain column "{col}"')

    adc_serials = df['adc_serial'].to_numpy()
    adc_channels = df['adc_0in_chan'].to_numpy()
    enabled_flags = df['ch_enabled'].to_numpy()

    # Ensure all three columns have the same length
    n = adc_serials.shape[0]
    if adc_channels.shape[0] != n or enabled_flags.shape[0] != n:
        raise ValueError('MOAS CSV: "adc_serial", "adc_0in_chan" and "ch_enabled" columns must have the same length')

    # Return arrays so caller can use them to update reg config
    return adc_serials, adc_channels, enabled_flags

def set_enabled_channels(version):
    """Set the enabled channel configuration from the MOAS into the AFI reg config file.
    """
    cfg = Config().parse_yaml()
    
    #reg_config_path = get_active_reg_config(cfg)
        # Determine ADC64 JSON file path. Prefer explicit path, otherwise try afi_config_path
    adc64_path = cfg.get("adc64_reg_config_path")
    if not adc64_path:
        raise ValueError("adc64_reg_config_path not configured in YAML; cannot locate reg ADC64 default.json")
    reg_config_path = Path(adc64_path)
    
    adc_serials, adc_channels, enabled_flags = get_enabled_channels(version, cfg)

    # Load existing reg config
    if not reg_config_path.exists():
        raise FileNotFoundError(f"AFI reg config file not found: {reg_config_path}")
    with open(reg_config_path, 'r') as f:
        reg_config = json.load(f)
    # Update enabled channels in reg config
    known_setups = reg_config.get('config', {}).get('knownSetups', {})
    if not known_setups:
        raise KeyError('reg_config missing config.knownSetups')

    def _find_known_setup_key(moas_serial: str):
        """Find a knownSetups key that corresponds to the MOAS adc_serial.

        Matching is done case-insensitively and by substring so keys like
        '0xDF:0x00000CD94138' will match a MOAS serial '0CD94138'.
        """
        s = str(moas_serial).lower()
        for key in known_setups:
            if s in key.lower():
                return key
        return None

    updated = defaultdict(list)
    # iterate over rows and update chAdcEn for the matching known setup
    for serial, chan, flag in zip(adc_serials, adc_channels, enabled_flags):
        key = _find_known_setup_key(serial)
        if key is None:
            # skip or warn if no matching knownSetup found
            print(f"Warning: no knownSetups key found for ADC serial '{serial}'")
            continue

        # ensure path exists down to tqdc.chAdcEn
        ks = known_setups[key]
        if 'tqdc' not in ks:
            ks['tqdc'] = {}
        if 'chAdcEn' not in ks['tqdc']:
            ks['tqdc']['chAdcEn'] = {}

        chan_key = str(int(chan))
        new_val = bool(int(flag))
        # existing value may be missing or different
        old_val = ks['tqdc']['chAdcEn'].get(chan_key)
        # Compare normalized booleans; allow int/bool equivalence
        if old_val is None or bool(old_val) != new_val:
            ks['tqdc']['chAdcEn'][chan_key] = new_val
            updated[key].append((int(chan), new_val))

    # Save updated reg config
    with open(reg_config_path, 'w') as f:
        json.dump(reg_config, f, indent=4)

    # print summary
    if updated:
        print(f"Updated enabled channels in AFI reg config: {reg_config_path}")
        for k, changes in updated.items():
            print(f"  {k}: {len(changes)} channels updated")
    else:
        print("No channels updated (no matches found)")