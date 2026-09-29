#!/usr/bin/env python3
"""
Analyze aggregated architecture benchmark results.

Usage:
    python analyze_architectures.py results.json -o report

The input is expected to have architecture keys (e.g. push, poll, amqp, s3),
each containing testcase keys such as c5000-100 and c5000-100-payload.
Each testcase contains one or more repetitions with:
  raw.time.{total,spawn,drain}
  network.average.{tx,rx}
  lifetimes.{minimum,average,maximum,p10,p25,p50,p75,p90,p95,p99}

Outputs:
  - CSV with per-architecture/testcase aggregated metrics
  - PNG plots covering the main comparisons
  - textual summary.txt with automatically derived observations
"""

import argparse
import json
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ARCH_ORDER = ["push", "poll", "amqp", "s3"]
LOADS = [100, 50, 25, 10, 0]
METRICS = [
    "total_time", "spawn_time", "drain_time",
    "lifetime_avg", "p50", "p90", "p95", "p99", "max_lifetime",
    "tx_bytes_per_item", "rx_bytes_per_item",
]


def mean(xs):
    xs = [x for x in xs if x is not None and np.isfinite(x)]
    return float(np.mean(xs)) if xs else np.nan


def pct_change(new, old):
    if old == 0 or not np.isfinite(old) or not np.isfinite(new):
        return np.nan
    return 100.0 * (new / old - 1.0)


def parse_case(case):
    payload = case.endswith("-payload")
    base = case[:-8] if payload else case
    try:
        load = int(base.rsplit("-", 1)[1])
    except Exception:
        load = np.nan
    return load, payload


def load_data(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def aggregate(data):
    rows = []
    for arch, cases in data.items():
        for testcase, reps in cases.items():
            load, payload = parse_case(testcase)
            def vals(path):
                out = []
                for r in reps:
                    x = r
                    try:
                        for key in path:
                            x = x[key]
                        out.append(float(x))
                    except (KeyError, TypeError, ValueError):
                        pass
                return out

            row = {
                "architecture": arch,
                "testcase": testcase,
                "load": load,
                "payload": payload,
                "n_repetitions": len(reps),
                "total_time": mean(vals(["raw", "time", "total"])),
                "spawn_time": mean(vals(["raw", "time", "spawn"])),
                "drain_time": mean(vals(["raw", "time", "drain"])),
                "lifetime_avg": mean(vals(["lifetimes", "average"])),
                "p50": mean(vals(["lifetimes", "p50"])),
                "p90": mean(vals(["lifetimes", "p90"])),
                "p95": mean(vals(["lifetimes", "p95"])),
                "p99": mean(vals(["lifetimes", "p99"])),
                "max_lifetime": mean(vals(["lifetimes", "maximum"])),
                "tx_bytes_per_item": mean(vals(["network", "average", "tx"])),
                "rx_bytes_per_item": mean(vals(["network", "average", "rx"])),
            }
            rows.append(row)
    return pd.DataFrame(rows)


def setup():
    plt.rcParams.update({
        "figure.figsize": (10, 6),
        "axes.grid": True,
        "grid.alpha": 0.25,
        "font.size": 10,
        "axes.titlesize": 13,
        "axes.labelsize": 11,
        "legend.fontsize": 9,
    })


def save(fig, out, name):
    fig.tight_layout()
    fig.savefig(out / name, dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_total_vs_load(df, out):
    for payload in [False, True]:
        sub = df[df.payload == payload]
        fig, ax = plt.subplots()
        for arch in ARCH_ORDER:
            x = sub[sub.architecture == arch].sort_values("load")
            if not x.empty:
                ax.plot(x.load, x.total_time, marker="o", label=arch)
        ax.set_title(f"End-to-end test duration vs load {'(payload)' if payload else '(no payload)'}")
        ax.set_xlabel("Load")
        ax.set_ylabel("Total time (source time units)")
        ax.invert_xaxis()
        ax.legend()
        save(fig, out, f"01_total_vs_load_{'payload' if payload else 'plain'}.png")


def plot_latency_percentiles(df, out):
    for load in LOADS:
        for payload in [False, True]:
            sub = df[(df.load == load) & (df.payload == payload)].copy()
            if sub.empty:
                continue
            x = np.arange(len(sub))
            width = 0.16
            fig, ax = plt.subplots(figsize=(11, 6))
            for i, metric in enumerate(["p50", "p90", "p95", "p99"]):
                ax.bar(x + (i - 1.5) * width, sub[metric], width, label=metric)
            ax.set_xticks(x)
            ax.set_xticklabels(sub.architecture)
            ax.set_yscale("log")
            ax.set_title(f"Lifetime latency percentiles — load {load} {'(payload)' if payload else '(no payload)'}")
            ax.set_xlabel("Architecture")
            ax.set_ylabel("Latency (source time units, log scale)")
            ax.legend()
            save(fig, out, f"02_latency_load{load}_{'payload' if payload else 'plain'}.png")


def plot_drain_share(df, out):
    d = df.copy()
    d["drain_share_pct"] = 100 * d.drain_time / d.total_time
    for payload in [False, True]:
        sub = d[d.payload == payload]
        fig, ax = plt.subplots()
        for arch in ARCH_ORDER:
            x = sub[sub.architecture == arch].sort_values("load")
            if not x.empty:
                ax.plot(x.load, x.drain_share_pct, marker="o", label=arch)
        ax.set_title(f"Drain time as share of total runtime {'(payload)' if payload else '(no payload)'}")
        ax.set_xlabel("Load")
        ax.set_ylabel("Drain share (%)")
        ax.invert_xaxis()
        ax.set_ylim(bottom=0)
        ax.legend()
        save(fig, out, f"03_drain_share_{'payload' if payload else 'plain'}.png")


def plot_payload_overhead(df, out):
    rows = []
    for arch in df.architecture.unique():
        for load in LOADS:
            plain = df[(df.architecture == arch) & (df.load == load) & (~df.payload)]
            pay = df[(df.architecture == arch) & (df.load == load) & (df.payload)]
            if plain.empty or pay.empty:
                continue
            p = plain.iloc[0]
            q = pay.iloc[0]
            rows.append({
                "architecture": arch, "load": load,
                "network_multiplier": q.tx_bytes_per_item / p.tx_bytes_per_item,
                "time_change_pct": pct_change(q.total_time, p.total_time),
            })
    ov = pd.DataFrame(rows)
    if ov.empty:
        return

    fig, ax = plt.subplots()
    for arch in ARCH_ORDER:
        x = ov[ov.architecture == arch].sort_values("load")
        if not x.empty:
            ax.plot(x.load, x.network_multiplier, marker="o", label=arch)
    ax.axhline(1.0, linewidth=1)
    ax.set_title("Payload network overhead")
    ax.set_xlabel("Load")
    ax.set_ylabel("Payload / plain TX bytes per item")
    ax.invert_xaxis()
    ax.legend()
    save(fig, out, "04_payload_network_multiplier.png")

    fig, ax = plt.subplots()
    for arch in ARCH_ORDER:
        x = ov[ov.architecture == arch].sort_values("load")
        if not x.empty:
            ax.plot(x.load, x.time_change_pct, marker="o", label=arch)
    ax.axhline(0.0, linewidth=1)
    ax.set_title("Payload effect on total test duration")
    ax.set_xlabel("Load")
    ax.set_ylabel("Change vs plain (%)")
    ax.invert_xaxis()
    ax.legend()
    save(fig, out, "05_payload_time_change.png")


def plot_network(df, out):
    for payload in [False, True]:
        sub = df[df.payload == payload]
        fig, ax = plt.subplots()
        for arch in ARCH_ORDER:
            x = sub[sub.architecture == arch].sort_values("load")
            if not x.empty:
                ax.plot(x.load, x.tx_bytes_per_item, marker="o", label=arch)
        ax.set_title(f"Average TX bytes per item {'(payload)' if payload else '(no payload)'}")
        ax.set_xlabel("Load")
        ax.set_ylabel("TX bytes per item")
        ax.invert_xaxis()
        ax.legend()
        save(fig, out, f"06_network_tx_{'payload' if payload else 'plain'}.png")


def make_summary(df):
    lines = []
    lines.append("Architecture benchmark analysis")
    lines.append("=" * 34)
    lines.append("")
    lines.append("The script aggregates repetitions by arithmetic mean. Time units are preserved exactly as supplied by the JSON; the file does not label them, so the script does not assume ms/us/etc. Latency percentiles are means of the reported per-run percentiles.")
    lines.append("")

    # Overall timing at representative load points
    for payload in [False, True]:
        label = "payload" if payload else "plain"
        lines.append(f"[{label}] Total time by architecture and load")
        sub = df[df.payload == payload]
        for load in LOADS:
            x = sub[sub.load == load].sort_values("total_time")
            if not x.empty:
                vals = ", ".join(f"{r.architecture}={r.total_time:.0f}" for _, r in x.iterrows())
                lines.append(f"  load {load}: {vals}")
        lines.append("")

    # Latency contrast: poll vs push/amqp/s3
    for load in LOADS:
        for payload in [False, True]:
            sub = df[(df.load == load) & (df.payload == payload)].set_index("architecture")
            if "poll" not in sub.index:
                continue
            lines.append(f"[{'payload' if payload else 'plain'}] Load {load}: p99 lifetime latency")
            for arch in ["push", "amqp", "s3"]:
                if arch in sub.index:
                    ratio = sub.loc["poll", "p99"] / sub.loc[arch, "p99"]
                    lines.append(f"  poll / {arch}: {ratio:.1f}x")
            lines.append("")

    # Payload network multiplier
    lines.append("Payload network multiplier (TX bytes/item, payload/plain)")
    for arch in ARCH_ORDER:
        vals = []
        for load in LOADS:
            p = df[(df.architecture == arch) & (df.load == load) & (~df.payload)]
            q = df[(df.architecture == arch) & (df.load == load) & (df.payload)]
            if not p.empty and not q.empty:
                vals.append((load, q.iloc[0].tx_bytes_per_item / p.iloc[0].tx_bytes_per_item))
        if vals:
            lines.append("  " + arch + ": " + ", ".join(f"{l}={m:.2f}x" for l, m in vals))
    lines.append("")

    # Drain share / saturation signal
    d = df.copy()
    d["drain_share_pct"] = 100 * d.drain_time / d.total_time
    lines.append("High drain-share cases (potential completion/backlog effects)")
    top = d.sort_values("drain_share_pct", ascending=False).head(8)
    for _, r in top.iterrows():
        lines.append(
            f"  {r.architecture:5s} {r.testcase:18s}: "
            f"drain={r.drain_time:.0f}, total={r.total_time:.0f}, "
            f"share={r.drain_share_pct:.1f}%"
        )
    lines.append("")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", type=Path)
    ap.add_argument("-o", "--output", type=Path, default=Path("architecture_analysis"))
    args = ap.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)
    data = load_data(args.input)
    df = aggregate(data)
    df.to_csv(args.output / "aggregated_metrics.csv", index=False)

    setup()
    plot_total_vs_load(df, args.output)
    plot_latency_percentiles(df, args.output)
    plot_drain_share(df, args.output)
    plot_payload_overhead(df, args.output)
    plot_network(df, args.output)

    (args.output / "summary.txt").write_text(make_summary(df), encoding="utf-8")
    print(f"Wrote analysis to {args.output.resolve()}")


if __name__ == "__main__":
    main()
