from pathlib import Path
import json, glob, re, math, textwrap
import pandas as pd
import matplotlib.pyplot as plt

BASE_IN = Path("data/processed/aggregated")
BASE = Path("data/results")
INPUTS = sorted(BASE_IN.glob("*.json"))
INPUTS = [p for p in INPUTS if p.name not in {"benchmark_plot_data.json"}]

def discover_architectures(paths):
    """Load every aggregate JSON and derive the architecture/tag from its content."""
    records = {}
    for path in paths:
        with path.open() as f:
            data = json.load(f)
        tag = str(data["tag"])
        if tag in records:
            raise ValueError(f"Duplicate architecture tag {tag!r}: {records[tag]['path']} and {path}")
        records[tag] = {"path": path, "data": data}
    return dict(sorted(records.items()))

architectures = discover_architectures(INPUTS)
if not architectures:
    raise RuntimeError("No aggregate JSON files found.")

# Extract only fields required for plotting. Configuration identity remains the complete
# config object, while labels are derived from its actual fields.
rows = []
for tag, rec in architectures.items():
    data = rec["data"]
    for tc in data["testcases"]:
        cfg = tc["config"]
        if cfg.get("skip"):
            continue
        stats = tc["instance_statistics"]
        lifetime = stats["lifetime"]
        spawns = stats["spawns"]
        payload = cfg.get("instanceConfig", {}).get("payloadSize")
        delay = cfg.get("delayMs")
        label = cfg.get("label")
        rows.append({
            "architecture": tag,
            "source_file": rec["path"].name,
            "config_label": label,
            "delay_ms": delay,
            "payload_size": payload,
            "instance_count": cfg.get("instanceCount"),
            "spawn_rate": spawns["avg_spawns_per_second"],
            "complete_rate": spawns["avg_completes_per_second"],
            "spawn_ci_low": spawns["run_level_avg_spawns_per_second"].get("ci_low"),
            "spawn_ci_high": spawns["run_level_avg_spawns_per_second"].get("ci_high"),
            "complete_ci_low": spawns["run_level_avg_completes_per_second"].get("ci_low"),
            "complete_ci_high": spawns["run_level_avg_completes_per_second"].get("ci_high"),
            "p50": lifetime.get("p50"),
            "p90": lifetime.get("p90"),
            "p95": lifetime.get("p95"),
            "p99": lifetime.get("p99"),
            "lifetime_mean": lifetime.get("mean"),
            "run_count": tc.get("run_count"),
        })

df = pd.DataFrame(rows)
df = df.sort_values(["architecture", "delay_ms", "payload_size", "config_label"]).reset_index(drop=True)
df.to_csv(BASE / "benchmark_plot_data_v2.csv", index=False)

# Fixed semantic styles: percentile identity is carried by line style/marker, not random colors.
PCTL_STYLE = {
    "p50": {"linestyle": "-",  "marker": "o", "linewidth": 2.0},
    "p95": {"linestyle": "--", "marker": "s", "linewidth": 2.0},
    "p99": {"linestyle": ":",  "marker": "^", "linewidth": 2.2},
}
payload_values = sorted(x for x in df["payload_size"].dropna().unique())
payload_labels = {0: "payload = 0", 10000: "payload = 10,000"}
payload_labels.update({p: f"payload = {int(p):,}" for p in payload_values if p not in payload_labels})

# ---------- Per-architecture plots ----------
for tag in architectures:
    sub = df[df["architecture"] == tag]
    delays = sorted(sub["delay_ms"].unique())

    # Throughput: completion + spawn in the same figure; payload encoded by color,
    # metric encoded by line style. This remains stable as configs are added.
    fig, ax = plt.subplots(figsize=(9.5, 5.5))
    for payload in payload_values:
        s = sub[sub["payload_size"] == payload].sort_values("delay_ms")
        x = s["delay_ms"].to_numpy()
        for metric, style, label_suffix in [
            ("complete_rate", "-", "complete"),
            ("spawn_rate", "--", "spawn"),
        ]:
            y = s[metric].to_numpy()
            if metric == "complete_rate":
                lo = s["complete_ci_low"].to_numpy()
                hi = s["complete_ci_high"].to_numpy()
                ax.errorbar(
                    x, y, yerr=[y-lo, hi-y], fmt="o", linestyle=style,
                    capsize=3, linewidth=1.8, markersize=5,
                    label=f"{payload_labels[payload]}, {label_suffix}",
                )
            else:
                ax.plot(x, y, linestyle=style, marker="o", markersize=4,
                        linewidth=1.5, alpha=0.8,
                        label=f"{payload_labels[payload]}, {label_suffix}")
    ax.set_yscale("log")
    ax.set_xlabel("Configured delay (ms)")
    ax.set_ylabel("Throughput (events/s)")
    ax.set_title(f"{tag}: throughput by configuration")
    ax.set_xticks(delays)
    ax.grid(True, which="major", axis="y", alpha=0.25)
    ax.legend(ncol=2, frameon=False)
    fig.tight_layout()
    fig.savefig(BASE / f"{tag}_throughput_v2.png", dpi=180, bbox_inches="tight")
    plt.close(fig)

    # Lifetime: semantic percentile styling; payload gets separate panels so six curves
    # never collapse into an ambiguous color soup.
    fig, axes = plt.subplots(1, max(1, len(payload_values)),
                             figsize=(6.2 * max(1, len(payload_values)), 4.8),
                             sharey=True, squeeze=False)
    axes = axes[0]
    for ax, payload in zip(axes, payload_values):
        s = sub[sub["payload_size"] == payload].sort_values("delay_ms")
        for pctl, style in PCTL_STYLE.items():
            ax.plot(s["delay_ms"], s[pctl], label=pctl.upper(), **style)
        ax.set_title(payload_labels[payload])
        ax.set_xlabel("Configured delay (ms)")
        ax.set_xticks(delays)
        ax.grid(True, which="major", axis="y", alpha=0.25)
    axes[0].set_ylabel("Lifetime (source units)")
    axes[-1].legend(frameon=False, title="Pooled percentile")
    fig.suptitle(f"{tag}: lifetime percentiles", y=1.02)
    fig.tight_layout()
    fig.savefig(BASE / f"{tag}_lifetime_percentiles_v2.png", dpi=180, bbox_inches="tight")
    plt.close(fig)

# ---------- Scalable cross-architecture comparison ----------
# Small multiples use a shared axis instead of overlapping bars. Any number of architectures
# creates additional panels automatically.
tags = list(architectures)
n = len(tags)
ncols = min(3, max(1, n))
nrows = math.ceil(n / ncols)

fig, axes = plt.subplots(nrows, ncols, figsize=(5.2*ncols, 4.2*nrows),
                         sharex=True, sharey=True, squeeze=False)
axes = axes.ravel()

for i, tag in enumerate(tags):
    ax = axes[i]
    sub = df[df["architecture"] == tag]
    for payload in payload_values:
        s = sub[sub["payload_size"] == payload].sort_values("delay_ms")
        y = s["complete_rate"].to_numpy()
        lo = s["complete_ci_low"].to_numpy()
        hi = s["complete_ci_high"].to_numpy()
        ax.errorbar(
            s["delay_ms"], y, yerr=[y-lo, hi-y],
            marker="o", linewidth=1.8, capsize=3,
            label=payload_labels[payload],
        )
    ax.set_title(tag)
    ax.set_yscale("log")
    ax.set_xticks(sorted(sub["delay_ms"].unique()))
    ax.grid(True, which="major", axis="y", alpha=0.25)
    ax.set_xlabel("Delay (ms)")
    ax.set_ylabel("Completion throughput (events/s)")

for ax in axes[n:]:
    ax.remove()

handles, labels = axes[0].get_legend_handles_labels()
fig.legend(handles, labels, loc="upper center", ncol=max(1, len(payload_values)),
           frameon=False, bbox_to_anchor=(0.5, 1.01))
fig.suptitle("Completion throughput across architectures", y=1.06)
fig.tight_layout()
fig.savefig(BASE / "architecture_completion_throughput_v2.png", dpi=180, bbox_inches="tight")
plt.close(fig)

# Scalable secondary comparison: p95 lifetime, again as small multiples.
fig, axes = plt.subplots(nrows, ncols, figsize=(5.2*ncols, 4.2*nrows),
                         sharex=True, sharey=True, squeeze=False)
axes = axes.ravel()

for i, tag in enumerate(tags):
    ax = axes[i]
    sub = df[df["architecture"] == tag]
    for payload in payload_values:
        s = sub[sub["payload_size"] == payload].sort_values("delay_ms")
        ax.plot(s["delay_ms"], s["p95"], marker="o", linewidth=1.8,
                label=payload_labels[payload])
    ax.set_title(tag)
    ax.set_yscale("log")
    ax.set_xticks(sorted(sub["delay_ms"].unique()))
    ax.grid(True, which="major", axis="y", alpha=0.25)
    ax.set_xlabel("Delay (ms)")
    ax.set_ylabel("P95 lifetime (source units)")

for ax in axes[n:]:
    ax.remove()

handles, labels = axes[0].get_legend_handles_labels()
fig.legend(handles, labels, loc="upper center", ncol=max(1, len(payload_values)),
           frameon=False, bbox_to_anchor=(0.5, 1.01))
fig.suptitle("P95 lifetime across architectures", y=1.06)
fig.tight_layout()
fig.savefig(BASE / "architecture_p95_lifetime_v2.png", dpi=180, bbox_inches="tight")
plt.close(fig)

# A reusable source script is emitted separately so the plotting implementation is reproducible.
script = r'''#!/usr/bin/env python3
"""Scalable benchmark visualization generator.

Usage:
    python plot_benchmarks.py data/processed/aggregated/*.json --out-dir figures

Architecture/tag names are discovered from each aggregate JSON's `tag` field.
No architecture names are hard-coded. Configuration identity is the complete
`config` object; labels are derived from config fields.
"""
from pathlib import Path
import argparse, json, math
import pandas as pd
import matplotlib.pyplot as plt

PCTL_STYLE = {
    "p50": {"linestyle": "-",  "marker": "o", "linewidth": 2.0},
    "p95": {"linestyle": "--", "marker": "s", "linewidth": 2.0},
    "p99": {"linestyle": ":",  "marker": "^", "linewidth": 2.2},
}

def load(paths):
    records = {}
    for path in paths:
        path = Path(path)
        data = json.loads(path.read_text())
        tag = str(data["tag"])
        if tag in records:
            raise ValueError(f"Duplicate architecture tag: {tag}")
        records[tag] = {"path": path, "data": data}
    rows = []
    for tag, rec in sorted(records.items()):
        for tc in rec["data"]["testcases"]:
            cfg = tc["config"]
            if cfg.get("skip"):
                continue
            st = tc["instance_statistics"]
            lt, sp = st["lifetime"], st["spawns"]
            payload = cfg.get("instanceConfig", {}).get("payloadSize")
            rows.append({
                "architecture": tag,
                "source_file": rec["path"].name,
                "config_label": cfg.get("label"),
                "delay_ms": cfg.get("delayMs"),
                "payload_size": payload,
                "spawn_rate": sp["avg_spawns_per_second"],
                "complete_rate": sp["avg_completes_per_second"],
                "complete_ci_low": sp["run_level_avg_completes_per_second"].get("ci_low"),
                "complete_ci_high": sp["run_level_avg_completes_per_second"].get("ci_high"),
                "p50": lt.get("p50"), "p95": lt.get("p95"), "p99": lt.get("p99"),
                "lifetime_mean": lt.get("mean"),
                "run_count": tc.get("run_count"),
            })
    return pd.DataFrame(rows).sort_values(
        ["architecture", "delay_ms", "payload_size", "config_label"]
    )

def payload_label(value):
    return "payload = 0" if value == 0 else f"payload = {int(value):,}"

def plot(df, out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    tags = list(dict.fromkeys(df["architecture"]))
    payloads = sorted(df["payload_size"].dropna().unique())

    for tag in tags:
        sub = df[df.architecture == tag]
        delays = sorted(sub.delay_ms.unique())

        fig, ax = plt.subplots(figsize=(9.5, 5.5))
        for payload in payloads:
            s = sub[sub.payload_size == payload].sort_values("delay_ms")
            x, y = s.delay_ms, s.complete_rate
            lo, hi = s.complete_ci_low, s.complete_ci_high
            ax.errorbar(x, y, yerr=[y-lo, hi-y], marker="o", capsize=3,
                        linewidth=1.8, label=payload_label(payload))
            ax.plot(x, s.spawn_rate, "--", marker="o", alpha=.8,
                    label=f"{payload_label(payload)}, spawn")
        ax.set_yscale("log")
        ax.set_xlabel("Configured delay (ms)")
        ax.set_ylabel("Throughput (events/s)")
        ax.set_title(f"{tag}: throughput by configuration")
        ax.set_xticks(delays)
        ax.grid(True, which="major", axis="y", alpha=.25)
        ax.legend(ncol=2, frameon=False)
        fig.tight_layout()
        fig.savefig(out_dir / f"{tag}_throughput.png", dpi=180, bbox_inches="tight")
        plt.close(fig)

        fig, axes = plt.subplots(1, len(payloads), figsize=(6.2*len(payloads), 4.8),
                                 sharey=True, squeeze=False)
        axes = axes[0]
        for ax, payload in zip(axes, payloads):
            s = sub[sub.payload_size == payload].sort_values("delay_ms")
            for pctl, style in PCTL_STYLE.items():
                ax.plot(s.delay_ms, s[pctl], label=pctl.upper(), **style)
            ax.set_title(payload_label(payload))
            ax.set_xlabel("Configured delay (ms)")
            ax.set_xticks(delays)
            ax.grid(True, which="major", axis="y", alpha=.25)
        axes[0].set_ylabel("Lifetime (source units)")
        axes[-1].legend(frameon=False, title="Pooled percentile")
        fig.suptitle(f"{tag}: lifetime percentiles", y=1.02)
        fig.tight_layout()
        fig.savefig(out_dir / f"{tag}_lifetime_percentiles.png", dpi=180, bbox_inches="tight")
        plt.close(fig)

    n, ncols = len(tags), min(3, max(1, len(tags)))
    nrows = math.ceil(n / ncols)
    fig, axes = plt.subplots(nrows, ncols, figsize=(5.2*ncols, 4.2*nrows),
                             sharex=True, sharey=True, squeeze=False)
    axes = axes.ravel()
    for i, tag in enumerate(tags):
        ax = axes[i]
        sub = df[df.architecture == tag]
        for payload in payloads:
            s = sub[sub.payload_size == payload].sort_values("delay_ms")
            y, lo, hi = s.complete_rate, s.complete_ci_low, s.complete_ci_high
            ax.errorbar(s.delay_ms, y, yerr=[y-lo, hi-y], marker="o",
                        linewidth=1.8, capsize=3, label=payload_label(payload))
        ax.set_title(tag)
        ax.set_yscale("log")
        ax.set_xticks(sorted(sub.delay_ms.unique()))
        ax.set_xlabel("Delay (ms)")
        ax.set_ylabel("Completion throughput (events/s)")
        ax.grid(True, which="major", axis="y", alpha=.25)
    for ax in axes[n:]:
        ax.remove()
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=max(1, len(payloads)),
               frameon=False, bbox_to_anchor=(.5, 1.01))
    fig.suptitle("Completion throughput across architectures", y=1.06)
    fig.tight_layout()
    fig.savefig(out_dir / "architecture_completion_throughput.png", dpi=180, bbox_inches="tight")
    plt.close(fig)

    fig, axes = plt.subplots(nrows, ncols, figsize=(5.2*ncols, 4.2*nrows),
                             sharex=True, sharey=True, squeeze=False)
    axes = axes.ravel()
    for i, tag in enumerate(tags):
        ax = axes[i]
        sub = df[df.architecture == tag]
        for payload in payloads:
            s = sub[sub.payload_size == payload].sort_values("delay_ms")
            ax.plot(s.delay_ms, s.p95, marker="o", linewidth=1.8,
                    label=payload_label(payload))
        ax.set_title(tag)
        ax.set_yscale("log")
        ax.set_xticks(sorted(sub.delay_ms.unique()))
        ax.set_xlabel("Delay (ms)")
        ax.set_ylabel("P95 lifetime (source units)")
        ax.grid(True, which="major", axis="y", alpha=.25)
    for ax in axes[n:]:
        ax.remove()
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=max(1, len(payloads)),
               frameon=False, bbox_to_anchor=(.5, 1.01))
    fig.suptitle("P95 lifetime across architectures", y=1.06)
    fig.tight_layout()
    fig.savefig(out_dir / "architecture_p95_lifetime.png", dpi=180, bbox_inches="tight")
    plt.close(fig)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inputs", nargs="+", type=Path)
    ap.add_argument("--out-dir", type=Path, default=Path("figures"))
    args = ap.parse_args()
    df = load(args.inputs)
    df.to_csv(args.out_dir / "benchmark_plot_data.csv", index=False)
    plot(df, args.out_dir)

if __name__ == "__main__":
    main()
'''
(BASE / "plot_benchmarks.py").write_text(script)

print("Generated scalable plotting implementation and refreshed figures.")
print("Architectures discovered:", ", ".join(architectures))
print("Outputs:")
for p in sorted(BASE.glob("*_v2.png")):
    print(" -", p.name)
print(" - plot_benchmarks.py")
print(" - benchmark_plot_data_v2.csv")
