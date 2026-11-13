#!/usr/bin/env python3
"""
parse_apache_log.py - convert an Apache/Nginx "vhost combined" access log into
the CSV format score_bot_ips.py expects.

Expected input line format (one request per line):
  vhost ip - - [timestamp] "method path protocol" status bytes "referrer" "user_agent"

Usage:
  python3 parse_apache_log.py other_vhosts_access.log.anonimized --out real_access_log.csv

Output columns: row_id, timestamp, ip, method, path, status, bytes_sent, user_agent, referrer
(matches crawler_monitor_sample_logs.csv, so no COLUMNS edit is needed in score_bot_ips.py).
"""
import argparse
import csv
import re
import sys

# referrer/user_agent are matched greedily so a stray literal quote inside either
# field (e.g. XSS/SQLi probe payloads) doesn't break the split: the regex engine
# backtracks to the rightmost '" "' before the line's closing quote.
LINE_PATTERN = re.compile(
    r'^(?P<vhost>\S+) (?P<ip>\S+) \S+ \S+ \[(?P<ts>[^\]]+)\] '
    r'"(?P<method>\S+) (?P<path>\S+) \S+" (?P<status>\d+) (?P<bytes>\S+) '
    r'"(?P<referrer>.*)" "(?P<ua>.*)"$'
)


def convert(src, dst):
    written = skipped = 0
    with open(src, encoding="utf-8", errors="replace") as fin, \
         open(dst, "w", newline="", encoding="utf-8") as fout:
        writer = csv.writer(fout)
        writer.writerow(["row_id", "timestamp", "ip", "method", "path",
                          "status", "bytes_sent", "user_agent", "referrer"])
        for row_id, line in enumerate(fin):
            m = LINE_PATTERN.match(line.rstrip("\n"))
            if not m:
                skipped += 1
                continue
            writer.writerow([
                row_id, m["ts"], m["ip"], m["method"], m["path"],
                m["status"], m["bytes"], m["ua"], m["referrer"],
            ])
            written += 1
    return written, skipped


def main():
    p = argparse.ArgumentParser(description="Convert an Apache vhost-combined log to score_bot_ips.py's CSV format.")
    p.add_argument("log", help="input Apache/Nginx combined log file")
    p.add_argument("--out", default="access_log.csv", help="output CSV path")
    cfg = p.parse_args()

    written, skipped = convert(cfg.log, cfg.out)
    print(f"Wrote {written:,} rows to {cfg.out}, skipped {skipped:,} unparsable lines.", file=sys.stderr)


if __name__ == "__main__":
    main()
