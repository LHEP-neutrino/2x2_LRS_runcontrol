#!/usr/bin/env python3

import argparse
import datetime
import json
from pathlib import Path
import os
import re
import zlib
import numpy as np
import sqlite3
import warnings

import h5py

from lrscfg.client import Client
from lrscfg.config import Config

def get_checksum(path: Path):
    cksum = 1
    with open(path, 'rb') as f:
        chunksize = int(1e9)
        while data := f.read(chunksize):
            cksum = zlib.adler32(data, cksum)
    return cksum & 0xffffffff


def get_afi_config():
    """
    Load and return the AFI JSON configuration referenced by the YAML key
    'afi_config_path' from the application's parsed YAML config.

    Returns:
        dict: Parsed JSON content from the AFI config file.

    Raises:
        KeyError: if 'afi_config_path' is not present in the parsed YAML.
        FileNotFoundError: if the referenced JSON file does not exist.
        json.JSONDecodeError: if the file content is not valid JSON.
    """
    cfg = Config().parse_yaml()

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

    # Build the expected paths for the four JSON files
    expected = {
        'RunControl': afi_base / 'RunControl' / f"{env_name}_rctl" / 'default.json',
        'EvB': afi_base / 'EvB' / f"{env_name}_evbld" / 'default.json',
        'Adc64_sum': afi_base / 'Adc64' / f"{env_name}_sum" / 'default.json',
        'Adc64_reg': afi_base / 'Adc64' / f"{env_name}_reg" / 'default.json',
    }

    results = {}
    missing = []
    for key, p in expected.items():
        p = Path(p)
        if not p.exists():
            missing.append(str(p))
            continue
        try:
            with open(p, 'r') as jf:
                results[key] = json.load(jf)
        except Exception as e:
            raise RuntimeError(f"Failed to load JSON from {p}: {e}")

    if missing:
        raise FileNotFoundError(f"Missing AFI json files: {', '.join(missing)}")

    return results

def get_data_stream(f, args):
    if ds := args["data_stream"]:
        return ds
    return 'commissioning'

def get_data_tier(f):
    return 'raw'

def get_start_time(path: Path):
    return int(path.stat().st_ctime)

def get_end_time(path: Path):
    return int(path.stat().st_mtime)

def get_run(path: Path, args):
    if "run" in args.keys():
        if args["run"]:
            return args["run"]
    
    pattern = r"mpd_(.*?)_(\d+)_p(\d+)\.data"
    match = re.match(pattern, path.name)
    if match:
        _, run, _ = match.groups()
        return int(run)
    # Check second pattern if not found
    pattern = r"mpd_(.*?)_(\d+)\.data"
    match = re.match(pattern, path.name)
    if match:
        _, run = match.groups()
        return int(run)
    raise ValueError("Invalid filename format")

def get_subrun(path: Path, args):
    if "subrun" in args.keys():
        if args["subrun"]:
            return args["subrun"]
    pattern = r"mpd_(.*?)_(\d+)_p(\d+)\.data"
    match = re.match(pattern, path.name)
    if match:
        _, _, subrun = match.groups()
        return int(subrun)
    # Check second pattern if not found
    pattern = r"mpd_(.*?)_(\d+)\.data"
    match = re.match(pattern, path.name)
    if match:
        return 0
    else:
        raise ValueError("Invalid filename format of %s" % path.name)

def get_first_event(file, args: dict):
    # Define constants
    SYNC_BYTES_SIZE = 4
    TIMESTAMP_SIZE = 8
    TAI_SIZE = 4
    EVENT_HEADER_SIZE = SYNC_BYTES_SIZE + TIMESTAMP_SIZE + TAI_SIZE

    # Read first event timestamp
    with open(file, 'rb') as buf:
        while True:
            sync_bytes = buf.read(SYNC_BYTES_SIZE)
            if len(sync_bytes) < SYNC_BYTES_SIZE:
                break  # End of file reached
            sync = np.frombuffer(sync_bytes, dtype='u4')
            if sync == 0x2A50D5AF:
                buf.seek(8, 1)  # Skip to the timestamp
                timestamp_bytes = buf.read(TIMESTAMP_SIZE)
                if len(timestamp_bytes) < TIMESTAMP_SIZE:
                    raise ValueError("File ended unexpectedly while reading timestamp")
                unix_ms = np.frombuffer(timestamp_bytes, dtype='u8').item() // 1000  # ms to s
                buf.seek(12, 1)  # Skip to the timestamp
                tai_bytes = buf.read(TAI_SIZE)
                if len(tai_bytes) < TAI_SIZE:
                    raise ValueError("File ended unexpectedly while reading TAI timestamp")
                tai_s = np.frombuffer(tai_bytes, dtype='u4').item()
                
                return unix_ms, tai_s
    return -1, -1
    #raise ValueError("No event found in file")

def get_last_event(file, args: dict):
    CHUNK_SIZE = 4096 * 16

    with open(file, 'rb') as buf:
        buf.seek(0, 2)
        file_size = buf.tell()
        num_chunks = -(-file_size // CHUNK_SIZE)

        # Start from the end of the file and search in reverse
        for chunk_index in range(num_chunks):
            offset = max(0, file_size - (chunk_index + 1) * CHUNK_SIZE)
            read_size = min(CHUNK_SIZE, file_size - offset)
            buf.seek(offset)
            chunk_data = buf.read(read_size)
            sync_indices = np.where(np.frombuffer(chunk_data, dtype='u4') == 0x2A50D5AF)[0]

            if len(sync_indices) > 0:
                event_offset = offset + sync_indices[-1] * 4 + 12
                buf.seek(event_offset)
                unix_ms = np.frombuffer(buf.read(8), dtype='u8').item() // 1000  # ms to s
                buf.seek(12, 1)
                tai_s = np.frombuffer(buf.read(4), dtype='u4').item()
                return unix_ms, tai_s
    return -1, -1
    #raise ValueError("No event found in file")

def get_metadata(f, args):
    start_time_unix, start_time_tai = get_first_event(f, args)
    end_time_unix, end_time_tai = get_last_event(f, args)
    meta = {}
    path = Path(f)
    run = get_run(path, args)
    subrun = get_subrun(path, args)
    cl = Client()

    meta['name'] = path.name
    meta['namespace'] = 'neardet-2x2-lar-light'
    meta['checksums'] = {
        'adler32': f'{get_checksum(path):08x}'}
    meta['size'] = path.stat().st_size

    md = meta['metadata'] = {
        'core.application.family': 'lrs',
        'core.application.name': 'lrs_daq',
        'core.application.version': 'mpd-rcts4-1.4.3-v1.5',

        'core.data_stream': get_data_stream(f, args),
        'core.data_tier': get_data_tier(f),
        'core.file_type': 'detector',
        'core.file_format': 'binary',
        'core.file_content_status': 'good',

        'core.start_time': start_time_unix,
        'core.end_time': end_time_unix,

        'core.run_type': 'neardet-2x2-lar-light',

        'core.runs': [run],
        'core.runs_subruns': [10000*run + subrun],

        'core.first_event_number': start_time_tai, # set wr timestamp as unique event number
        'core.last_event_number': end_time_tai,

        'retention.class': 'rawdata',
        'retention.status': 'active',

        'dune.lrs_active_config': cl.get_active_moas(),
        'dune.lrs_active_thresholds': cl.get_active_foas(),
    }

    return meta

def dump_metadata(app, args):
    if app:
        app.logger.debug(f"Entered dump_meta")
    f = args['datafile']
    meta = get_metadata(f, args)
    if app:
        app.logger.debug(f"get_metadata done")
    jsonfile = Path(f).with_suffix(Path(f).suffix + '.json')
    if app:
        app.logger.info(f"Dumped metadata for {jsonfile}")
    with open(jsonfile, 'w') as outf:
        json.dump(meta, outf, indent=4)
        outf.write('\n')

    if 'database' in args:
        write_metadata_to_db(args['database'], meta, args)

def write_metadata_to_db(db_path, meta,args):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create table if it doesn't exist
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS lrs_runs_data (
        filename TEXT,
        size INTEGER,
        application_version TEXT,
        run_mode TEXT,
        start_time_unix INTEGER,
        end_time_unix INTEGER,
        run_start_instance TEXT,
        morcs_run_nr INTEGER,
        subrun INTEGER,
        first_event_tai INTEGER,
        last_event_tai INTEGER,
        active_moas TEXT,
        afi_runcontrol_json JSON,
        afi_evb_json JSON,
        afi_adc64_sum_json JSON,
        afi_adc64_reg_json JSON,
        active_foas TEXT
    )
    ''')

    # AFI JSONs should be provided at run start and attached to args under
    # 'afi_jsons'. Prefer those; otherwise attempt to load them here.
    afi_runcontrol = afi_evb = afi_adc64_sum = afi_adc64_reg = None
    afi_dict = None
    if isinstance(args, dict) and 'afi_jsons' in args:
        afi_dict = args.get('afi_jsons')
    else:
        afi_dict = None
        warnings.warn("AFI JSONs not provided in args; cannot write to DB")

    if afi_dict:
        afi_runcontrol = json.dumps(afi_dict.get('RunControl')) if 'RunControl' in afi_dict else None
        afi_evb = json.dumps(afi_dict.get('EvB')) if 'EvB' in afi_dict else None
        afi_adc64_sum = json.dumps(afi_dict.get('Adc64_sum')) if 'Adc64_sum' in afi_dict else None
        afi_adc64_reg = json.dumps(afi_dict.get('Adc64_reg')) if 'Adc64_reg' in afi_dict else None

    # Insert metadata into table (now with 4 extra columns)
    cursor.execute('''
    INSERT INTO lrs_runs_data (
        filename, 
        size, 
        application_version, 
        run_mode, 
        start_time_unix, 
        end_time_unix, 
        run_start_instance, 
        morcs_run_nr, 
        subrun, 
        first_event_tai, 
        last_event_tai, 
        active_moas,
        afi_runcontrol_json,
        afi_evb_json,
        afi_adc64_sum_json,
        afi_adc64_reg_json,
        active_foas
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        meta['name'],
        meta['size'],
        meta['metadata']['core.application.version'],
        meta['metadata']['core.data_stream'],
        meta['metadata']['core.start_time'],
        meta['metadata']['core.end_time'],
        args["run_starting_instance"],
        meta['metadata']['core.runs'][0],
        meta['metadata']['core.runs_subruns'][0],
        meta['metadata']['core.first_event_number'],
        meta['metadata']['core.last_event_number'],
        meta['metadata']['dune.lrs_active_config'],
        afi_runcontrol,
        afi_evb,
        afi_adc64_sum,
        afi_adc64_reg,
        meta['metadata']['dune.lrs_active_thresholds']
    ))

    conn.commit()
    conn.close()

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--datafile', type=Path)

    # NOTE: If any of the following are specified on the command line, they
    # override whatever might be stored in the attrs of `/meta` in the hdf5
    # file. If nothing is specified on the command line, and nothing is in
    # `/meta`, then `get_data_stream` etc. will return a default value.
    ap.add_argument('--data_stream',type=str)
    ap.add_argument('--run_starting_instance',type=str)
    # ap.add_argument('--run-type')
    ap.add_argument('--run', type=int, default=None)
    ap.add_argument('--subrun', type=int, default=None)
    ap.add_argument('--first-event', type=int)
    ap.add_argument('--last-event', type=int)
    ap.add_argument('--database', type=Path, help='Path to the SQLite database')

    args = vars(ap.parse_args())

    dump_metadata(None,args)
