#!/usr/bin/env python3
"""
remap_csv_columns.py - rename a CSV's columns to the names score_bot_ips.py
expects (ip, path, status, user_agent, referrer), for logs that are already
CSV but use different column names. Keeps COLUMNS in score_bot_ips.py
untouched, so one dataset's naming doesn't break the others.

Usage:
  python3 remap_csv_columns.py eclog_1day.csv --out eclog_1day_mapped.csv \
      --map ip=IpId --map path=Uri --map status=ResponseCode \
      --map user_agent=UserAgent --map referrer=Referrer
"""
import argparse

import pandas as pd


def main():
    p = argparse.ArgumentParser(description="Rename CSV columns to score_bot_ips.py's expected names.")
    p.add_argument("csv", help="input CSV file")
    p.add_argument("--out", required=True, help="output CSV path")
    p.add_argument("--map", action="append", required=True, metavar="OURS=THEIRS",
                   help="column rename, e.g. --map ip=IpId (repeatable)")
    p.add_argument("--sep", default=",", help="column separator of the input (default: ,)")
    cfg = p.parse_args()

    rename = dict(item.split("=", 1)[::-1] for item in cfg.map)  # {theirs: ours}

    df = pd.read_csv(cfg.csv, sep=cfg.sep, dtype=str, keep_default_na=False)
    missing = [theirs for theirs in rename if theirs not in df.columns]
    if missing:
        raise SystemExit(f"Missing column(s) in {cfg.csv}: {', '.join(missing)}. "
                          f"Columns found: {', '.join(df.columns)}")
    df = df.rename(columns=rename)
    df.to_csv(cfg.out, index=False)
    print(f"Wrote {len(df):,} rows to {cfg.out}")


if __name__ == "__main__":
    main()
