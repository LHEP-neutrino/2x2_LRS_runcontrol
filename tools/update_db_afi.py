#!/usr/bin/env python3
"""
Update existing rows in the lrs_runs_data SQLite table with AFI JSONs.

Usage examples:
  # update specific filenames
  python3 tools/update_db_afi.py --db /path/to/lrsdb.db --filenames mpd_a_1.data,mpd_b_2.data

  # update by run numbers
  python3 tools/update_db_afi.py --db /path/to/lrsdb.db --runs 123,124

  # update all rows
  python3 tools/update_db_afi.py --db /path/to/lrsdb.db --all

  # dry-run (shows what would be updated)
  python3 tools/update_db_afi.py --db /path/to/lrsdb.db --filenames x.data --dry-run

This script uses the repository's `get_afi_config()` function to load the AFI JSONs based
on current configuration. Run this script from the repository root or pass a full path
for --db. Ensure your PYTHONPATH or sys.path includes the repo root. If you use the
`lrsctrlenv` conda env, activate it first.
"""

import argparse
import sys
import sqlite3
import json
from pathlib import Path

# Ensure repo root is importable
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from lrsctrl.metadata import get_afi_config


def parse_list_arg(s):
    if not s:
        return []
    return [x.strip() for x in s.split(',') if x.strip()]


def ensure_columns(cursor):
    cursor.execute("PRAGMA table_info(lrs_runs_data)")
    cols = [r[1] for r in cursor.fetchall()]
    needed = ['afi_runcontrol_json', 'afi_evb_json', 'afi_adc64_sum_json', 'afi_adc64_reg_json']
    missing = [c for c in needed if c not in cols]
    return missing


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', required=True, help='Path to the SQLite DB')
    ap.add_argument('--filenames', help='Comma-separated list of filenames to update')
    ap.add_argument('--runs', help='Comma-separated list of morcs_run_nr integers to update')
    ap.add_argument('--all', action='store_true', help='Update all rows')
    ap.add_argument('--afi-runcontrol', help='Path to a RunControl AFI JSON file to use')
    ap.add_argument('--afi-evb', help='Path to an EvB AFI JSON file to use')
    ap.add_argument('--afi-adc64-sum', help='Path to an Adc64 sum AFI JSON file to use')
    ap.add_argument('--afi-adc64-reg', help='Path to an Adc64 reg AFI JSON file to use')
    ap.add_argument('--dry-run', action='store_true', help='Show rows to be updated but do not write')
    args = ap.parse_args()

    db_path = Path(args.db).expanduser().resolve()
    if not db_path.exists():
        print(f"DB not found: {db_path}")
        raise SystemExit(1)

    filenames = parse_list_arg(args.filenames)
    runs = parse_list_arg(args.runs)

    if not (args.all or filenames or runs):
        print("Specify --filenames, --runs or --all")
        raise SystemExit(1)

    # Load AFI JSONs. User may provide explicit file paths; otherwise try to load
    # from the current config using get_afi_config(). If some explicit paths are
    # provided and others are not, we will try to fill the rest from the
    # configuration.
    afi_runcontrol = afi_evb = afi_adc64_sum = afi_adc64_reg = None

    provided_any = any((args.afi_runcontrol, args.afi_evb, args.afi_adc64_sum, args.afi_adc64_reg))
    afi_dict = {}

    def load_json_path(pth):
        p = Path(pth).expanduser()
        if not p.exists():
            raise FileNotFoundError(f"AFI json file not found: {p}")
        with open(p, 'r') as jf:
            return json.load(jf)

    # Load explicit paths first
    if args.afi_runcontrol:
        try:
            afi_dict['RunControl'] = load_json_path(args.afi_runcontrol)
        except Exception as e:
            print(f"Failed to load --afi-runcontrol: {e}")
            raise SystemExit(2)
    if args.afi_evb:
        try:
            afi_dict['EvB'] = load_json_path(args.afi_evb)
        except Exception as e:
            print(f"Failed to load --afi-evb: {e}")
            raise SystemExit(2)
    if args.afi_adc64_sum:
        try:
            afi_dict['Adc64_sum'] = load_json_path(args.afi_adc64_sum)
        except Exception as e:
            print(f"Failed to load --afi-adc64-sum: {e}")
            raise SystemExit(2)
    if args.afi_adc64_reg:
        try:
            afi_dict['Adc64_reg'] = load_json_path(args.afi_adc64_reg)
        except Exception as e:
            print(f"Failed to load --afi-adc64-reg: {e}")
            raise SystemExit(2)

    # If any missing and none were provided, or if some were provided and others
    # are missing, attempt to load the remaining ones using get_afi_config().
    need_fill = set(['RunControl', 'EvB', 'Adc64_sum', 'Adc64_reg']) - set(afi_dict.keys())
    if need_fill:
        try:
            cfg_dict = get_afi_config()
        except Exception as e:
            if provided_any:
                # If user provided some files, it's OK to continue with those only
                cfg_dict = {}
                warnings.warn(f"Could not load remaining AFI configs from config path: {e}")
            else:
                print(f"Failed to load AFI configs from config path: {e}")
                raise SystemExit(2)

        for k in list(need_fill):
            if k in cfg_dict:
                afi_dict[k] = cfg_dict[k]

    afi_runcontrol = json.dumps(afi_dict.get('RunControl')) if 'RunControl' in afi_dict else None
    afi_evb = json.dumps(afi_dict.get('EvB')) if 'EvB' in afi_dict else None
    afi_adc64_sum = json.dumps(afi_dict.get('Adc64_sum')) if 'Adc64_sum' in afi_dict else None
    afi_adc64_reg = json.dumps(afi_dict.get('Adc64_reg')) if 'Adc64_reg' in afi_dict else None

    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()

    missing = ensure_columns(cur)
    if missing:
        print('The database is missing expected columns:', missing)
        print('Please migrate the database or ensure the table has the new JSON columns.')
        conn.close()
        raise SystemExit(3)

    # Build query to select rows
    where_clauses = []
    params = []
    if filenames:
        placeholders = ','.join('?' for _ in filenames)
        where_clauses.append(f"filename IN ({placeholders})")
        params.extend(filenames)
    if runs:
        placeholders = ','.join('?' for _ in runs)
        where_clauses.append(f"morcs_run_nr IN ({placeholders})")
        params.extend([int(r) for r in runs])
    if args.all:
        where = ''
    else:
        where = 'WHERE ' + ' OR '.join(where_clauses)

    select_sql = f"SELECT filename, morcs_run_nr FROM lrs_runs_data {where}"
    cur.execute(select_sql, params)
    rows = cur.fetchall()
    if not rows:
        print('No rows matched the selection')
        conn.close()
        return

    print(f'Found {len(rows)} rows to update:')
    for fn, runnr in rows:
        print(' -', fn, runnr)

    if args.dry_run:
        print('\nDry run; no changes written.')
        conn.close()
        return

    update_sql = (
        'UPDATE lrs_runs_data SET afi_runcontrol_json=?, afi_evb_json=?, afi_adc64_sum_json=?, afi_adc64_reg_json=? '
        + ('WHERE ' + ' OR '.join(where_clauses) if not args.all else 'WHERE 1=1')
    )

    # We will update each selected row individually by filename to avoid mistakes
    for fn, runnr in rows:
        cur.execute(
            'UPDATE lrs_runs_data SET afi_runcontrol_json=?, afi_evb_json=?, afi_adc64_sum_json=?, afi_adc64_reg_json=? WHERE filename=?',
            (afi_runcontrol, afi_evb, afi_adc64_sum, afi_adc64_reg, fn)
        )

    conn.commit()
    conn.close()
    print('Update completed.')

if __name__ == '__main__':
    main()
