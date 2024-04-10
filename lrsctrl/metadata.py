#!/usr/bin/env python3

# COPYIED from https://github.com/larpix/crs_daq/blob/feature-metadata/dump_metadata.py

import argparse
import datetime
import json
from pathlib import Path
import os, re
import zlib
import numpy as np

import h5py


def get_checksum(path: Path):
    cksum = 1
    with open(path, 'rb') as f:
        chunksize = int(1e9)
        while data := f.read(chunksize):
            cksum = zlib.adler32(data, cksum)
    return cksum & 0xffffffff


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
    if run := args["run"]:
        return run
    
    pattern = r"mpd_(.*?)_(\d+)_p(\d+)\.data"
    match = re.match(pattern, path.name)
    if match:
        _, run, _ = match.groups()
        return int(run)
    #Check second pattern if not found
    pattern = r"mpd_(.*?)_(\d+)\.data"
    match = re.match(pattern, path.name)
    if match:
        _, run = match.groups()
        return int(run)
    raise ValueError("Invalid filename format")


def get_subrun(path: Path, args):
    if subrun := args["subrun"]:
        return subrun
    
    pattern = r"mpd_(.*?)_(\d+)_p(\d+)\.data"
    match = re.match(pattern, path.name)
    if match:
        _, _, subrun = match.groups()
        return int(subrun)
    else:
        raise ValueError("Invalid filename format")


def get_first_event(file, args: dict):
    #if first_event := args["first_event"]:
    #    return first_event
    
    #Read first event timestamp
    with open(file,'rb') as buf:
        while sync := np.frombuffer(buf.read(4), dtype = 'u4'):
            if not sync:
                break
            elif sync == 0x2A50D5AF:
                buf.seek(8, 1)  # Skip to the timestamp
                unix_ms = np.frombuffer(buf.read(8), dtype='u8').item()//1000 #ms to s
                buf.seek(12, 1)
                tai_s = np.frombuffer(buf.read(4), dtype='u4').item()
                return unix_ms, tai_s

    raise ValueError("No event found in file")


def get_last_event(file, args: dict):
    CHUNK_SIZE = 4096*16

    with open(file, 'rb') as buf:
        buf.seek(0, 2)
        file_size = buf.tell()
        print(file_size)
        num_chunks = -(-file_size // CHUNK_SIZE)
        print(num_chunks)

        # Start from the end of the file and search in reverse
        for chunk_index in range(num_chunks):
            offset = max(0, file_size - (chunk_index + 1) * CHUNK_SIZE)
            read_bits = min(file_size,CHUNK_SIZE)
            buf.seek(offset)
            sync_indices = np.where(np.frombuffer(buf.read(CHUNK_SIZE), dtype='u4') == 0x2A50D5AF)[0]

            if len(sync_indices) > 0:
                print(sync_indices)
                event_offset = offset + sync_indices[-1] * 4 + 12
                buf.seek(event_offset)
                unix_ms = np.frombuffer(buf.read(8), dtype='u8').item()//1000 #ms to s
                buf.seek(12, 1)
                tai_s = np.frombuffer(buf.read(4), dtype='u4').item()
                return unix_ms, tai_s

    raise ValueError("No event found in file")


def get_metadata(f, args):
    start_time_unix, start_time_tai = get_first_event(f, args)
    end_time_unix, end_time_tai = get_last_event(f, args)
    meta = {}
    path = Path(f)

    meta['name'] = path.name
    meta['namespace'] = 'neardet-2x2-lar-light'
    meta['checksums'] = {
        'adler32': f'{get_checksum(path):08x}'}
    meta['size'] = path.stat().st_size

    md = meta['metadata'] = {
        'core.application.family': 'lrs',
        'core.application.name': 'lrs_daq',
        'core.application.version': 'mpd-rcts3-1.4.3-v1.1',

        'core.data_stream': get_data_stream(f, args),
        'core.data_tier': get_data_tier(f),
        'core.file_type': 'detector',
        'core.file_format': 'binary',
        'core.file_content_status': 'good',

        'core.start_time': get_start_time(path),
        'core.end_time': get_end_time(path),

        'core.run_type': 'neardet-2x2-lar-light',

        'core.runs': [get_run(f, args)],
        'core.runs_subruns': [get_subrun(f, args)],

        'core.first_event_number': start_time_tai, # set wr timestamp as unique event number
        'core.last_event_number': end_time_tai,

        'retention.class': 'rawdata',
        'retention.status': 'active'
    }

    return meta

def dump_metadata(args):
    f = args['datafile']
    meta = get_metadata(f,args)

    jsonfile = Path(f).with_suffix(Path(f).suffix + '.json')
    with open(jsonfile, 'w') as outf:
        json.dump(meta, outf, indent=4)
        outf.write('\n')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('datafile', type=Path)

    # NOTE: If any of the following are specified on the command line, they
    # override whatever might be stored in the attrs of `/meta` in the hdf5
    # file. If nothing is specified on the command line, and nothing is in
    # `/meta`, then `get_data_stream` etc. will return a default value.
    ap.add_argument('--data-stream')
    # ap.add_argument('--run-type')
    ap.add_argument('--run', type=int)
    ap.add_argument('--subrun', type=int)
    ap.add_argument('--first-event', type=int)
    ap.add_argument('--last-event', type=int)

    args = vars(ap.parse_args())

    dump_metadata(args)

if __name__ == '__main__':
    main()