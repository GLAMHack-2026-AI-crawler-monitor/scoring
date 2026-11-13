#!/usr/bin/env python3
"""
score_bot_ips.py - score every IP address in a web access log (CSV) for
bot-like behaviour, using five warning signs worth one point each:

  1. flag_ua        Suspicious or fake robot name tag (user agent)
  2. flag_long      Absurdly long requests (very many query parameters / very long URLs)
  3. flag_noref     Never arrives via a link (no referrer on any request)
  4. flag_slowdown  Often gets "slow down" replies (HTTP 429 / 503)
  5. flag_onething  Does almost only one kind of request

  Score 0-1  -> looks like a human or a well-behaved bot
  Score 2    -> suspicious, worth a look
  Score 3-5  -> likely a bot

Expected CSV columns (edit COLUMNS below if yours are named differently):
  ip, path, status, user_agent, referrer

Usage:
  python src/score_bot_ips.py crawler_monitor_sample_logs.csv
  python src/score_bot_ips.py logs.csv --out ip_scores.csv --top 30
  python src/score_bot_ips.py logs.csv --verify-dns     # also check claimed crawlers via DNS

Requires: pandas  (pip install pandas)
"""
import argparse
import socket
import sys

import numpy as np
import pandas as pd

# Names of the columns in YOUR csv file (right side) -> names used by this script (left side)
COLUMNS = {
    "ip": "ip",
    "path": "path",
    "status": "status",
    "user_agent": "user_agent",
    "referrer": "referrer",
}

# Status codes that mean "slow down" / "server overloaded"
SLOWDOWN_CODES = {429, 503}

# Values that mean "no referrer"
NO_REFERRER = {"", "-"}

# A "robot name tag": a word in the user agent containing bot / crawl / spider / slurp
CRAWLER_PATTERN = r"([a-z0-9_-]*(?:bot|crawl|spider|slurp)[a-z0-9_-]*)"

# Programming libraries, command-line tools and headless browsers
TOOL_PATTERN = (
    r"python-requests|python-urllib|aiohttp|httpx|curl/|wget/|go-http-client|java/|"
    r"okhttp|scrapy|node-fetch|axios|libwww-perl|headlesschrome|phantomjs"
)

# Crawlers that can be verified by reverse DNS (only used with --verify-dns).
# The real crawler's IP must resolve to a host name ending in one of these domains,
# and that host name must resolve back to the same IP.
# Other operators (e.g. many AI crawlers) publish IP lists instead; those are not checked here.
VERIFY_DOMAINS = {
    "googlebot": (".googlebot.com", ".google.com"),
    "bingbot": (".search.msn.com",),
    "applebot": (".applebot.apple.com",),
    "yandexbot": (".yandex.ru", ".yandex.net", ".yandex.com"),
    "baiduspider": (".baidu.com", ".baidu.jp"),
}


def dns_confirms(ip, domains):
    """Forward-confirmed reverse DNS: IP -> host name -> back to the same IP."""
    try:
        host = socket.gethostbyaddr(ip)[0].lower().rstrip(".")
        if not host.endswith(domains):
            return False
        forward_ips = {info[4][0] for info in socket.getaddrinfo(host, None)}
        return ip in forward_ips
    except OSError:
        return False


def load_log(path, sep):
    df = pd.read_csv(path, sep=sep, dtype=str, keep_default_na=False)
    df = df.rename(columns={theirs: ours for ours, theirs in COLUMNS.items()})
    missing = [c for c in COLUMNS if c not in df.columns]
    if missing:
        sys.exit(f"Missing column(s) in {path}: {', '.join(missing)}. "
                 f"Columns found: {', '.join(df.columns)}. Edit COLUMNS at the top of the script.")
    return df


def score_ips(df, cfg):
    path = df["path"].str.strip()
    path_only = path.str.partition("?")[0]
    query = path.str.partition("?")[2]
    ua = df["user_agent"].str.strip()
    status = pd.to_numeric(df["status"], errors="coerce")

    n_params = query.str.count("&") + (query != "").astype(int)
    crawler_name = ua.str.extract(CRAWLER_PATTERN, flags=2)[0].str.lower()  # flags=2 is re.IGNORECASE
    page_type = path_only.str.extract(r"^/*([^/]*)")[0].str.lower().replace("", "(root)")

    req = pd.DataFrame({
        "ip": df["ip"].str.strip(),
        "n_params": n_params,
        "is_long": (n_params > cfg.max_params) | (path.str.len() > cfg.max_url_len),
        "has_ref": ~df["referrer"].str.strip().isin(NO_REFERRER),
        "is_slowdown": status.isin(SLOWDOWN_CODES),
        "crawler_name": crawler_name,
        "is_crawler": crawler_name.notna(),
        "is_tool": ua.str.contains(TOOL_PATTERN, case=False, regex=True) | ua.isin(["", "-"]),
        "is_robots": path_only.str.lower() == "/robots.txt",
        "page_type": page_type,
    })

    g = req.groupby("ip", sort=False)
    out = pd.DataFrame({
        "requests": g.size(),
        "long_requests": g["is_long"].sum(),
        "max_params": g["n_params"].max(),
        "referrer_share": g["has_ref"].mean(),
        "slowdown_share": g["is_slowdown"].mean(),
        "crawler_requests": g["is_crawler"].sum(),
        "n_crawler_names": g["crawler_name"].nunique(),
        "crawler_names": g["crawler_name"].agg(lambda s: ", ".join(sorted(s.dropna().unique()))),
        "tool_requests": g["is_tool"].sum(),
        "read_robots_txt": g["is_robots"].any(),
    })

    # Most common kind of request per IP, e.g. "bitstream", "search", "discover"
    counts = req.groupby(["ip", "page_type"]).size().rename("n").reset_index()
    top = counts.loc[counts.groupby("ip")["n"].idxmax()].set_index("ip")
    out["top_type"] = top["page_type"]
    out["top_type_share"] = top["n"] / out["requests"]

    # --- Warning sign 1: suspicious or fake robot name tag -----------------
    out["several_names"] = out["n_crawler_names"] > 1
    out["mixed_names"] = (out["crawler_requests"] > 0) & (out["crawler_requests"] < out["requests"])
    out["tool_name"] = out["tool_requests"] > 0
    out["no_robots"] = (out["crawler_requests"] >= cfg.robots_min_requests) & ~out["read_robots_txt"]
    out["dns_fail"] = False
    if cfg.verify_dns:
        socket.setdefaulttimeout(3)
        for ip, names in out.loc[out["crawler_requests"] > 0, "crawler_names"].items():
            for name in names.split(", "):
                for prefix, domains in VERIFY_DOMAINS.items():
                    if name.startswith(prefix) and not dns_confirms(ip, domains):
                        out.loc[ip, "dns_fail"] = True
    out["flag_ua"] = out[["several_names", "mixed_names", "tool_name", "no_robots", "dns_fail"]].any(axis=1)

    # --- Warning signs 2-5 ------------------------------------------------
    enough = out["requests"] >= cfg.min_requests
    out["flag_long"] = out["long_requests"] >= cfg.long_min_count
    out["flag_noref"] = enough & (out["referrer_share"] == 0)
    out["flag_slowdown"] = enough & (out["slowdown_share"] > cfg.slowdown_share)
    out["flag_onething"] = enough & (out["top_type_share"] > cfg.onething_share)

    flags = ["flag_ua", "flag_long", "flag_noref", "flag_slowdown", "flag_onething"]
    out["score"] = out[flags].sum(axis=1)
    out["label"] = np.select(
        [out["score"] >= 3, out["score"] == 2, ~enough],
        ["likely bot", "suspicious", "too few requests"],
        "likely human / well-behaved bot",
    )
    out["reasons"] = out.apply(explain, axis=1)

    out[flags] = out[flags].astype(int)
    for col in ["referrer_share", "slowdown_share", "top_type_share"]:
        out[col] = out[col].round(3)

    keep = ["requests", "score", "label", "reasons", *flags, "crawler_names", "max_params",
            "long_requests", "referrer_share", "slowdown_share", "top_type", "top_type_share",
            "read_robots_txt"]
    return (out[keep].rename_axis("ip").reset_index()
            .sort_values(["score", "requests"], ascending=[False, False]))


def explain(row):
    """Plain-language list of the warning signs that fired for one IP."""
    reasons = []
    if row["several_names"]:
        reasons.append(f"claims {row['n_crawler_names']} different crawler names ({row['crawler_names']})")
    if row["mixed_names"]:
        reasons.append("mixes crawler and browser names")
    if row["tool_name"]:
        reasons.append("scripting tool, headless browser or empty name")
    if row["no_robots"]:
        reasons.append("crawler that never read robots.txt")
    if row["dns_fail"]:
        reasons.append("crawler name not confirmed by DNS")
    if row["flag_long"]:
        reasons.append(f"{row['long_requests']} absurdly long requests (up to {row['max_params']} parameters)")
    if row["flag_noref"]:
        reasons.append(f"no referrer on any of {row['requests']} requests")
    if row["flag_slowdown"]:
        reasons.append(f"{row['slowdown_share']:.0%} 'slow down' replies")
    if row["flag_onething"]:
        reasons.append(f"{row['top_type_share']:.0%} of requests are '{row['top_type']}'")
    return "; ".join(reasons)


def main():
    p = argparse.ArgumentParser(description="Score IPs in an access-log CSV for bot-like behaviour.")
    p.add_argument("csv", help="input CSV file")
    p.add_argument("--out", default="ip_scores.csv", help="output CSV (default: ip_scores.csv)")
    p.add_argument("--sep", default=",", help="column separator of the input (default: ,)")
    p.add_argument("--top", type=int, default=20, help="how many top-scoring IPs to print (default: 20)")
    p.add_argument("--verify-dns", action="store_true",
                   help="check Googlebot/Bingbot/etc. claims with reverse DNS (slow, needs internet)")
    p.add_argument("--min-requests", type=int, default=10,
                   help="signs 3-5 only count for IPs with at least this many requests (default: 10)")
    p.add_argument("--max-params", type=int, default=10,
                   help="a request with more query parameters than this is 'absurdly long' (default: 10)")
    p.add_argument("--max-url-len", type=int, default=1000,
                   help="a URL longer than this is 'absurdly long' (default: 1000)")
    p.add_argument("--long-min-count", type=int, default=2,
                   help="number of absurdly long requests needed for sign 2 (default: 2)")
    p.add_argument("--slowdown-share", type=float, default=0.05,
                   help="sign 4 fires above this share of 429/503 replies (default: 0.05)")
    p.add_argument("--onething-share", type=float, default=0.80,
                   help="sign 5 fires above this share of one request type (default: 0.80)")
    p.add_argument("--robots-min-requests", type=int, default=50,
                   help="a crawler with at least this many requests should have read robots.txt (default: 50)")
    cfg = p.parse_args()

    df = load_log(cfg.csv, cfg.sep)
    result = score_ips(df, cfg)
    result.to_csv(cfg.out, index=False)

    print(f"Read {len(df):,} requests from {result.shape[0]:,} IPs.\n")
    print(result["label"].value_counts().to_string(), "\n")
    print(f"Top {cfg.top} IPs by score:")
    print(f"{'IP':<40} {'requests':>8} {'score':>5}  {'label':<32} reasons")
    for row in result.head(cfg.top).itertuples():
        print(f"{row.ip:<40} {row.requests:>8} {row.score:>5}  {row.label:<32} {row.reasons}")
    print(f"\nFull results written to {cfg.out}")


if __name__ == "__main__":
    main()
