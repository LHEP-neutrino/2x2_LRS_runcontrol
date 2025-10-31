import pandas as pd
import numpy as np
import subprocess
import csv
import sys
import os
import json
import shutil
from collections import defaultdict

from lrscfg.config import Config

def get_thresholds(version=None, source='FOAS'):
    """Return (channels, thresholds).

    source: 'FOAS' (default) or 'MOAS'.
    - FOAS: expects a CSV with columns 'channel' and 'threshold'. If `version` is provided
      it is treated as the FOAS filename (absolute or relative); otherwise the function
      will look for files named 'foas.csv'|'FOAS.csv'|'foas_example.csv' in the
      configured path.
    - MOAS: retains the previous behaviour and requires `version` (used as the
      MOAS version suffix to build filename 'MOAS_{version}.csv' inside moas_path).
    """
    cfg = Config().parse_yaml()

    source = (source or 'FOAS').upper()
    if source == 'FOAS':
        # FOAS files are named FOAS_{foas_version}.csv and stored in foas_path
        if not version:
            raise ValueError("FOAS source requires a foas_version (pass it as 'version')")
        base = cfg.get('foas_path')
        if not base:
            raise ValueError("foas_path not configured in YAML; cannot locate FOAS file")

        filename = f"FOAS_{version}.csv"
        foas_file = os.path.join(base, filename)
        if not os.path.exists(foas_file):
            raise FileNotFoundError(f"FOAS file not found: {foas_file}")

        df = pd.read_csv(foas_file)
        # Expect columns 'channel', 'threshold' and 'trig_active' together
        required = ('channel', 'threshold', 'trig_active')
        for col in required:
            if col not in df.columns:
                raise ValueError(f'FOAS CSV must contain column "{col}"')

        channels = df['channel'].to_numpy()
        thresholds = df['threshold'].to_numpy()
        trig_vals = df['trig_active'].to_numpy()

        # Ensure all three columns have the same length
        n = channels.shape[0]
        if thresholds.shape[0] != n or trig_vals.shape[0] != n:
            raise ValueError('FOAS CSV: "channel", "threshold" and "trig_active" columns must have the same length')

        # FOAS contains exactly one row per ADC channel (0..63). Validate rows and
        # collect mappings; do not allow duplicates.
        thr_map = {}
        trig_map = {}
        for idx, (ch_raw, th_raw, tr_raw) in enumerate(zip(channels, thresholds, trig_vals)):
            try:
                ch = int(float(ch_raw))
            except Exception:
                raise ValueError(f"Non-integer channel value at row {idx}: {ch_raw!r}")

            if ch in thr_map:
                raise ValueError(f"Duplicate channel {ch!r} found in FOAS file at row {idx}")

            # Validate threshold integerness and range
            try:
                th = int(float(th_raw))
            except Exception:
                raise ValueError(f"Non-integer threshold value for channel {ch!r}: {th_raw!r}")
            if not np.isclose(float(th_raw), float(th)):
                raise ValueError(f"Non-integer threshold value for channel {ch!r}: {th_raw!r}")
            if th < 0 or th > 32767:
                raise ValueError(f"Threshold {th} for channel {ch!r} out of allowed range [0, 32767]")

            thr_map[ch] = th

            # Convert trig_active to bool
            trig_map[ch] = to_bool(tr_raw, ch=ch)

        # Ensure exactly the 64 channels 0..63 are present
        expected = set(range(64))
        found = set(thr_map.keys())
        if found != expected:
            missing = sorted(expected - found)
            extra = sorted(found - expected)
            msgs = []
            if missing:
                msgs.append(f"missing channels: {missing}")
            if extra:
                msgs.append(f"unexpected channels: {extra}")
            raise ValueError("FOAS channel set mismatch: " + "; ".join(msgs))

        unique_channels = sorted(thr_map.keys())
        unique_thresholds = [thr_map[ch] for ch in unique_channels]
        unique_trig_flags = [trig_map[ch] for ch in unique_channels]

        return unique_channels, unique_thresholds, unique_trig_flags

    elif source == 'MOAS':
        if not version:
            raise ValueError('MOAS source requires a version (moas_version)')

        filename = f"MOAS_{version}.csv"
        path = cfg.get('moas_path')
        if not path:
            raise ValueError('moas_path not configured in YAML')
        df = pd.read_csv(os.path.join(path, filename))

        # Use pandas arrays directly
        sum_chan = df['sum_chan'].to_numpy()
        thresholds = df['threshold'].to_numpy()

        # Validate lengths
        if sum_chan.shape[0] != thresholds.shape[0]:
            raise ValueError("MOAS CSV: 'sum_chan' and 'threshold' columns have different lengths")

        # Group thresholds by channel
        grouped = defaultdict(list)
        # Preserve first-seen channel order
        seen = []
        for ch, th in zip(sum_chan, thresholds):
            grouped[ch].append(th)
            if ch not in seen:
                seen.append(ch)

        unique_channels = []
        unique_thresholds = []

        for ch in seen:
            th_list = grouped[ch]
            # Expect exactly six entries per channel
            if len(th_list) != 6:
                raise ValueError(f"Channel {ch!r} has {len(th_list)} entries in MOAS file; expected 6")

            # Convert all values to integers (allow floats that are whole numbers)
            int_vals = []
            for v in th_list:
                try:
                    # Handle values like '123.0' or numeric types
                    iv = int(float(v))
                except Exception:
                    raise ValueError(f"Non-integer threshold value for channel {ch!r}: {v!r}")
                # Verify conversion didn't lose information (e.g., 12.3 -> 12 should be rejected)
                if not np.isclose(float(v), float(iv)):
                    raise ValueError(f"Non-integer threshold value for channel {ch!r}: {v!r}")
                # Range check
                if iv < 0 or iv > 32767:
                    raise ValueError(f"Threshold {iv} for channel {ch!r} out of allowed range [0, 32767]")
                int_vals.append(iv)

            # Ensure all six integer values match
            if not all(iv == int_vals[0] for iv in int_vals):
                raise ValueError(f"Threshold mismatch for channel {ch!r}: values={int_vals}")

            unique_channels.append(ch)
            unique_thresholds.append(int_vals[0])
        # Return lists where each channel appears once with its verified integer threshold
        # MOAS has no trig flags, so return None for that element for compatibility
        return unique_channels, unique_thresholds, None

    else:
        raise ValueError(f"Unknown source '{source}'; expected 'FOAS' or 'MOAS'")


def set_thresholds(version, source='FOAS'):
    """Read thresholds via get_thresholds and write them into the ADC64 default.json.

    The ADC64 default.json path is taken from Config().parse_yaml()["adc64_sum_config_path"].
    If that value is a directory the file `default.json` inside it is used. A backup
    of the original file is created with a .bak suffix before writing.

    Returns the path written to on success.
    """
    cfg_yaml = Config().parse_yaml()

    # Determine ADC64 JSON file path. Prefer explicit path, otherwise try afi_config_path
    adc64_path = cfg_yaml.get("adc64_sum_config_path")
    if not adc64_path:
        raise ValueError("adc64_sum_config_path not configured in YAML; cannot locate ADC64 default.json")
    # The user-supplied path is expected to include the filename (default.json)

    if not os.path.exists(adc64_path):
        raise FileNotFoundError(f"ADC64 config file not found: {adc64_path}")

    # Get validated channels, thresholds and optional trig flags (FOAS by default)
    channels, thresholds, trig_flags = get_thresholds(version, source=source)

    # Load JSON
    with open(adc64_path, "r", encoding="utf-8") as fh:
        cfg = json.load(fh)

    # Update only the tqdc.chDigThr inside the knownSetups entry for this ADC serial
    cfg.setdefault("config", {})
    config_section = cfg["config"]
    config_section.setdefault("defaultSetup", {})

    # Read ADC serial key from YAML. User should add e.g. adc64_serial: "0xDF:0x00000CD9415C"
    serial_key = cfg_yaml.get("sum_adc64_serial")
    if not serial_key:
        raise ValueError("Please set 'adc64_serial' (the knownSetups key) in config.yaml to identify which knownSetups entry to update")

    # Ensure knownSetups exists
    config_section.setdefault("knownSetups", {})
    known = config_section["knownSetups"]

    # Do NOT create a missing knownSetup; require it to already exist
    if serial_key not in known:
        raise KeyError(f"Known setup for serial '{serial_key}' not found in ADC64 config; refusing to create it. Please add the knownSetups entry to default.json or set 'adc64_serial' to an existing key in config.yaml.")

    target = known[serial_key]
    # Ensure tqdc/chDigThr path exists in the known setup
    target.setdefault("tqdc", {})
    target_tqdc = target["tqdc"]
    target_tqdc.setdefault("chDigThr", {})
    chdig = target_tqdc["chDigThr"]

    # Update chDigThr entries (keys as strings to match file format)
    for ch, th in zip(channels, thresholds):
        chdig[str(ch)] = int(th)

    # Update chDigTrigEn as booleans
    if trig_flags is not None:
        target_tqdc.setdefault("chDigTrigEn", {})
        chtrigen = target_tqdc["chDigTrigEn"]
        for ch, flag in zip(channels, trig_flags):
            chtrigen[str(ch)] = bool(flag)

    # Backup original file
    #bak_path = adc64_path + ".bak"
    #shutil.copy2(adc64_path, bak_path)

    # Write updated JSON back
    with open(adc64_path, "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, indent=4)

def to_bool(val, ch=None):
    if isinstance(val, (np.bool_, bool)):
        return bool(val)
    try:
        ival = int(float(val))
        return bool(ival)
    except Exception:
        sval = str(val).strip().lower()
        if sval in ('1', 'true', 'yes', 'y', 't'):
            return True
        if sval in ('0', 'false', 'no', 'n', 'f'):
            return False
        if ch is None:
            raise ValueError(f"Cannot interpret trig_active value: {val!r}")
        raise ValueError(f"Cannot interpret trig_active value for channel {ch!r}: {val!r}")
    
    

