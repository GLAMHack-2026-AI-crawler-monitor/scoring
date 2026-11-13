#!/usr/bin/env python3
"""
generate_synthetic_log.py - build a larger synthetic access log by resampling
crawler_monitor_sample_logs.csv, for stress-testing score_bot_ips.py at
realistic data volumes (e.g. ~1 GB).

Each repeat resamples all rows with replacement and shifts the last IP octet,
so the result has more unique IPs than a plain concatenation would (worse
case for the per-IP groupby than just repeating the same 121 addresses).

Usage:
  python3 src/generate_synthetic_log.py --out data/synthetic_stress_log.csv --target-bytes 1100000000
"""
import argparse
import os

import pandas as pd


def build(base_path, target_bytes, seed):
    df = pd.read_csv(base_path, dtype=str, keep_default_na=False)
    file_bytes = os.path.getsize(base_path)
    repeats = max(1, int(target_bytes / file_bytes) + 1)

    chunks = []
    for i in range(repeats):
        chunk = df.sample(frac=1.0, replace=True, random_state=seed + i).copy()
        ip_parts = chunk["ip"].str.rsplit(".", n=1, expand=True)
        new_last = (ip_parts[1].astype(int) + i * 7) % 256
        chunk["ip"] = ip_parts[0] + "." + new_last.astype(str)
        chunk["row_id"] = range(len(chunk))
        chunks.append(chunk)
    return pd.concat(chunks, ignore_index=True)


def main():
    p = argparse.ArgumentParser(description="Generate a larger synthetic access log for stress-testing.")
    p.add_argument("--base", default="crawler_monitor_sample_logs.csv", help="base CSV to resample from")
    p.add_argument("--out", default="synthetic_stress_log.csv", help="output CSV path")
    p.add_argument("--target-bytes", type=int, default=1_100_000_000, help="approximate output file size in bytes")
    p.add_argument("--seed", type=int, default=0, help="random seed")
    cfg = p.parse_args()

    big = build(cfg.base, cfg.target_bytes, cfg.seed)
    big.to_csv(cfg.out, index=False)
    print(f"Wrote {len(big):,} rows ({big['ip'].nunique():,} unique IPs) to {cfg.out} "
          f"({os.path.getsize(cfg.out):,} bytes)")


if __name__ == "__main__":
    main()
