import argparse
import csv
import math
import os
from collections import defaultdict
import matplotlib.pyplot as plt

def percentile(sorted_vals, p):
    if not sorted_vals:
        return None
    if p <= 0:
        return sorted_vals[0]
    if p >= 100:
        return sorted_vals[-1]
    k = (len(sorted_vals) - 1) * (p / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_vals[int(k)]
    d0 = sorted_vals[f] * (c - k)
    d1 = sorted_vals[c] * (k - f)
    return d0 + d1

def load_rows(path):
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)

def to_int(x):
    try:
        return int(x)
    except Exception:
        return None

def to_float(x):
    try:
        return float(x)
    except Exception:
        return None

def matches_fixed_size(row, r_fixed, d_fixed):
    topo = row.get("topology", "")
    if topo in ("mesh", "torus2d"):
        return to_int(row.get("r")) == r_fixed
    if topo == "dq":
        return to_int(row.get("d")) == d_fixed
    return False

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True,)
    ap.add_argument("--r", type=int, default=14,)
    ap.add_argument("--d", type=int, default=5,)
    ap.add_argument("--outdir", default="plots")
    ap.add_argument("--title", default="FCT vs bg_num_flows (fixed size)")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    rows = load_rows(args.csv)
    filtered = []

    for row in rows:
        if not matches_fixed_size(row, args.r, args.d):
            continue
        fct = to_float(row.get("probe_fct_sec"))
        if fct is None:
            continue
        row["_fct"] = fct
        row["_bg_num_flows"] = to_int(row.get("bg_num_flows"))
        if row["_bg_num_flows"] is None:
            continue
        filtered.append(row)

    samples = defaultdict(list)
    for row in filtered:
        key = (row["topology"], row["_bg_num_flows"])
        samples[key].append(row["_fct"])

    stats = defaultdict(dict)
    for (topo, bg), vals in samples.items():
        vals_sorted = sorted(vals)
        stats[topo][bg] = {"n": len(vals_sorted), "median": percentile(vals_sorted, 50), "p95": percentile(vals_sorted, 95), "p99": percentile(vals_sorted, 99),}

    topos = sorted(stats.keys())
    print(f"\nSummary for fixed size: mesh/torus r={args.r}, dq d={args.d}")
    print("topology,bg_num_flows,n,median_sec,p95_sec,p99_sec")
    for topo in topos:
        for bg in sorted(stats[topo].keys()):
            s = stats[topo][bg]
            print(f"{topo},{bg},{s['n']},{s['median']:.6f},{s['p95']:.6f},{s['p99']:.6f}")

    def plot_metric(metric, ylabel, filename):
        plt.figure()
        for topo in topos:
            bgs = sorted(stats[topo].keys())
            ys = [stats[topo][bg][metric] for bg in bgs]
            plt.plot(bgs, ys, linestyle="-", marker="o", label=topo)
            
        plt.xlabel("bg_num_flows")
        plt.ylabel(ylabel)
        plt.title(args.title + f" — {metric}")
        plt.legend()
        plt.tight_layout()
        outpath = os.path.join(args.outdir, filename)
        plt.savefig(outpath, dpi=200)
        print(f"Wrote {outpath}")

    plot_metric("median", "seconds", f"incast_fct_median_r{args.r}_d{args.d}.png")
    plot_metric("p95", "seconds", f"incast_fct_p95_r{args.r}_d{args.d}.png")
    plot_metric("p99", "seconds", f"incast_fct_p99_r{args.r}_d{args.d}.png")

if __name__ == "__main__":
    main()
#   python3 analysis/analyze_fct_vs_bg.py --csv results_*traffic_type*.csv --r 14 --d 5 --outdir plots