#!/usr/bin/env python3
"""
plot_ip_scores.py - Python/matplotlib version of the dashboard (dashboard/).
Reads a score_bot_ips.py output CSV and steps through the same charts one at
a time: close a window (or press q) to see the next one.

Usage:
  python3 src/plot_ip_scores.py data/ip_scores_sample.csv
  python3 src/plot_ip_scores.py data/ip_scores_sample.csv --save-dir plots/   # save PNGs instead of opening windows

Requires: matplotlib, pandas, numpy
"""
import argparse
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Same labels/colours as dashboard/docs/index.md's LABEL_DOMAIN/LABEL_COLORS,
# so the two dashboards read the same way.
LABEL_DOMAIN = ["likely bot", "suspicious", "likely human / well-behaved bot", "too few requests"]
LABEL_COLORS = {
    "likely bot": "#e15759",
    "suspicious": "#f28e2b",
    "likely human / well-behaved bot": "#59a14f",
    "too few requests": "#bab0ac",
}

SCATTER_CAP = 5000  # dashboard/docs/index.md's SCATTER_CAP
GRID_COLS, GRID_ROWS = 40, 20  # dashboard/docs/index.md's GRID_COLS/GRID_ROWS
GRID_CELLS = GRID_COLS * GRID_ROWS


def show_or_save(fig, name, save_dir):
    if save_dir:
        path = save_dir / f"{name}.png"
        fig.savefig(path, dpi=150, bbox_inches="tight")
        print(f"Saved {path}")
        plt.close(fig)
    else:
        plt.show()


def plot_summary(df, save_dir):
    counts = df["label"].value_counts()
    cards = [
        ("IPs scored", len(df)),
        ("Likely bot", counts.get("likely bot", 0)),
        ("Suspicious", counts.get("suspicious", 0)),
        ("Likely human", counts.get("likely human / well-behaved bot", 0)),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(6, 4))
    fig.suptitle("Summary")
    for ax, (title, value) in zip(axes.flat, cards):
        ax.axis("off")
        ax.text(0.5, 0.6, f"{value:,}", ha="center", va="center", fontsize=28, fontweight="bold")
        ax.text(0.5, 0.2, title, ha="center", va="center", fontsize=12, color="#666666")
    show_or_save(fig, "summary", save_dir)


def plot_score_distribution(df, save_dir):
    pivot = df.pivot_table(index="score", columns="label", values="ip", aggfunc="count", fill_value=0)
    pivot = pivot.reindex(index=range(6), fill_value=0)
    pivot = pivot.reindex(columns=[l for l in LABEL_DOMAIN if l in pivot.columns], fill_value=0)

    fig, ax = plt.subplots(figsize=(7, 4))
    bottom = np.zeros(len(pivot))
    for label in pivot.columns:
        ax.bar(pivot.index, pivot[label], bottom=bottom, color=LABEL_COLORS[label], label=label)
        bottom += pivot[label].to_numpy()
    ax.set_xlabel("warning signs (score)")
    ax.set_ylabel("number of IPs")
    ax.set_title("Score distribution")
    ax.legend(fontsize=8)
    show_or_save(fig, "score_distribution", save_dir)


def plot_requests_vs_score(df, save_dir, rng):
    data = df if len(df) <= SCATTER_CAP else df.sample(SCATTER_CAP, random_state=rng.integers(2**31))
    sampled_note = f" (random sample of {SCATTER_CAP:,} of {len(df):,} IPs)" if len(df) > SCATTER_CAP else ""

    fig, ax = plt.subplots(figsize=(7, 4))
    for label in LABEL_DOMAIN:
        sub = data[data["label"] == label]
        if sub.empty:
            continue
        ax.scatter(sub["requests"], sub["score"], s=12, alpha=0.7, color=LABEL_COLORS[label], label=label)
    ax.set_xscale("log")
    ax.set_xlabel("requests")
    ax.set_ylabel("score")
    ax.set_title(f"Requests vs. score{sampled_note}")
    ax.legend(fontsize=8)
    show_or_save(fig, "requests_vs_score", save_dir)


def build_request_grid(df, n, rng):
    """Allocate n grid cells across labels, proportional to each label's share
    of total requests (largest-remainder rounding), mirroring
    dashboard/docs/index.md's buildRequestGrid() - see that file's comment for
    why allocation must happen per label, not per individual IP. Returns
    (label, score) pairs, shuffled, so the same draw can be rendered as-is
    (unsorted) or re-sorted by score without redrawing."""
    totals = df.groupby("label")["requests"].sum()
    total = totals.sum()
    exact = totals / total * n if total else totals * 0.0
    base = np.floor(exact).astype(int)
    remaining = n - int(base.sum())
    frac_order = (exact - base).sort_values(ascending=False).index
    for label in frac_order[:remaining]:
        base[label] += 1

    cells = []
    for label, count in base.items():
        if count == 0:
            continue
        sub = df[df["label"] == label]
        weights = sub["requests"].to_numpy(dtype=float)
        probs = weights / weights.sum()
        chosen = rng.choice(len(sub), size=count, p=probs)
        scores = sub["score"].to_numpy()[chosen]
        cells.extend(zip([label] * len(chosen), scores))
    rng.shuffle(cells)
    return cells[:n]


def sort_cells_by_label_count(cells):
    """Group cells by label into solid blocks, ordered from the most-populous
    label to the least, so the mosaic fills top-left to bottom-right one
    color at a time instead of shuffled or scattered by score."""
    counts = Counter(label for label, _ in cells)
    rank = {label: i for i, label in enumerate(sorted(counts, key=counts.get, reverse=True))}
    return sorted(cells, key=lambda cell: rank[cell[0]])


def render_request_mosaic(cells, title, name, save_dir):
    """Render (label, score) cells into the grid, filled column-major
    (top-to-bottom within a column, then the next column to the right) in
    the order given - callers sort/shuffle beforehand."""
    labels = np.array([label for label, _ in cells])
    grid = labels.reshape(GRID_ROWS, GRID_COLS, order="F")
    color_grid = np.ones((GRID_ROWS, GRID_COLS, 3))
    for label in LABEL_DOMAIN:
        hexcode = LABEL_COLORS[label].lstrip("#")
        rgb = tuple(int(hexcode[i:i + 2], 16) / 255 for i in (0, 2, 4))
        color_grid[grid == label] = rgb

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.imshow(color_grid, aspect="equal")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title(title)
    handles = [plt.Rectangle((0, 0), 1, 1, color=LABEL_COLORS[l]) for l in LABEL_DOMAIN]
    ax.legend(handles, LABEL_DOMAIN, loc="upper center", bbox_to_anchor=(0.5, -0.03), ncol=2, fontsize=8, frameon=False)
    show_or_save(fig, name, save_dir)


def plot_request_mosaic(df, save_dir, rng):
    cells = build_request_grid(df, GRID_CELLS, rng)
    render_request_mosaic(
        cells,
        f"Request mosaic (each of {GRID_CELLS} squares ≈ 1/{GRID_CELLS} of requests)",
        "request_mosaic", save_dir,
    )

    cells_by_label = sort_cells_by_label_count(cells)
    render_request_mosaic(
        cells_by_label,
        f"Request mosaic, grouped by label (each of {GRID_CELLS} squares ≈ 1/{GRID_CELLS} of requests)",
        "request_mosaic_sorted", save_dir,
    )


def main():
    p = argparse.ArgumentParser(
        description="Python/matplotlib version of dashboard/: steps through the same charts one at a time."
    )
    p.add_argument("csv", help="score_bot_ips.py output CSV (e.g. ip_scores_sample.csv)")
    p.add_argument("--save-dir", help="save each chart as a PNG here instead of opening a window")
    p.add_argument("--seed", type=int, default=0, help="random seed for sampling/mosaic draws (default: 0)")
    cfg = p.parse_args()

    df = pd.read_csv(cfg.csv)
    rng = np.random.default_rng(cfg.seed)

    save_dir = None
    if cfg.save_dir:
        save_dir = Path(cfg.save_dir)
        save_dir.mkdir(parents=True, exist_ok=True)

    plot_summary(df, save_dir)
    plot_score_distribution(df, save_dir)
    plot_requests_vs_score(df, save_dir, rng)
    plot_request_mosaic(df, save_dir, rng)


if __name__ == "__main__":
    main()
