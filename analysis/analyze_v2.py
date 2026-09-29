#!/usr/bin/env python3
"""Analyze process-engine benchmark results.

Usage:
    python analyze_architectures.py results.json -o architecture_analysis
    python analyze_architectures.py results.json --config testcases.jsonc -o architecture_analysis

The testcase configuration establishes that c5000-X means:
  - 5000 process instances
  - X milliseconds between instance starts
and that the -payload variants use a 10,000-byte instance payload.

The result JSON is expected to contain architecture keys such as push, poll,
amqp and s3, each with testcase arrays containing raw.time, network and
lifetimes measurements.
"""
from matplotlib.ticker import ScalarFormatter
import argparse
import json
import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ARCH_ORDER = ["push", "poll", "amqp", "s3"]
DELAYS_MS = [100, 50, 25, 10, 0]
PERCENTILES = ["p50", "p90", "p95", "p99"]
DRAIN_NOISE_FLOOR_MS = 2000  # below this, the measurement setup is effectively zero


def mean(values):
    values = [v for v in values if v is not None and np.isfinite(v)]
    return float(np.mean(values)) if values else np.nan


def pct_change(new, old):
    if old == 0 or not np.isfinite(old) or not np.isfinite(new):
        return np.nan
    return 100.0 * (new / old - 1.0)


def parse_case(label):
    payload = label.endswith("-payload")
    base = label[:-8] if payload else label
    m = re.fullmatch(r"c(\d+)-(\d+)", base)
    if not m:
        return np.nan, np.nan, payload
    return int(m.group(1)), int(m.group(2)), payload


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_config(path):
    if path is None:
        return None
    # JSONC here is currently ordinary JSON, but tolerate // comments and
    # trailing commas for convenience.
    text = Path(path).read_text(encoding="utf-8")
    text = re.sub(r"//.*?$", "", text, flags=re.MULTILINE)
    text = re.sub(r",\s*([}\]])", r"\1", text)
    return json.loads(text)


def extract(repetition, path):
    x = repetition
    try:
        for key in path:
            x = x[key]
        return float(x)
    except (KeyError, TypeError, ValueError):
        return None


def aggregate(results):
    rows = []
    for architecture, cases in results.items():
        if not isinstance(cases, dict):
            continue
        for testcase, repetitions in cases.items():
            instance_count, delay_ms, payload = parse_case(testcase)
            if not isinstance(repetitions, list):
                continue
            rows.append({
                "architecture": architecture,
                "testcase": testcase,
                "instance_count": instance_count,
                "delay_ms": delay_ms,
                "payload": payload,
                "payload_bytes": 10000 if payload else 0,
                "n_repetitions": len(repetitions),
                "total_time_ms": mean([extract(r, ["raw", "time", "total"]) for r in repetitions]),
                "spawn_time_ms": mean([extract(r, ["raw", "time", "spawn"]) for r in repetitions]),
                "drain_time_ms": mean([extract(r, ["raw", "time", "drain"]) for r in repetitions]),
                "effective_drain_ms": max(0.0, mean([extract(r, ["raw", "time", "drain"]) for r in repetitions]) - DRAIN_NOISE_FLOOR_MS),
                "overload": mean([extract(r, ["raw", "time", "drain"]) for r in repetitions]) >= DRAIN_NOISE_FLOOR_MS,
                "lifetime_avg_ms": mean([extract(r, ["lifetimes", "average"]) for r in repetitions]),
                "p50_ms": mean([extract(r, ["lifetimes", "p50"]) for r in repetitions]),
                "p90_ms": mean([extract(r, ["lifetimes", "p90"]) for r in repetitions]),
                "p95_ms": mean([extract(r, ["lifetimes", "p95"]) for r in repetitions]),
                "p99_ms": mean([extract(r, ["lifetimes", "p99"]) for r in repetitions]),
                "max_lifetime_ms": mean([extract(r, ["lifetimes", "maximum"]) for r in repetitions]),
                "tx_bytes_per_instance": mean([extract(r, ["network", "average", "tx"]) for r in repetitions]),
                "rx_bytes_per_instance": mean([extract(r, ["network", "average", "rx"]) for r in repetitions]),
            })
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


def series(df, architecture, payload):
    return df[(df.architecture == architecture) & (df.payload == payload)].sort_values("delay_ms")


def plot_total_duration(df, out):
    for payload in [False, True]:
        fig, ax = plt.subplots()
        for arch in ARCH_ORDER:
            x = series(df, arch, payload)
            if not x.empty:
                ax.plot(x.delay_ms, x.total_time_ms, marker="o", label=arch)
        ax.set_title(f"End-to-end test duration vs inter-instance delay {'(10 KB payload)' if payload else '(no payload)'}")
        ax.set_xlabel("Inter-instance delay (ms)")
        ax.set_ylabel("Total test duration (ms)")
        ax.invert_xaxis()
        ax.legend()
        save(fig, out, f"01_total_duration_{'payload' if payload else 'plain'}.png")


def plot_spawn_drain(df, out):
    for payload in [False, True]:
        fig, ax = plt.subplots()
        for arch in ARCH_ORDER:
            x = series(df, arch, payload)
            if not x.empty:
                ax.plot(x.delay_ms, x.spawn_time_ms, marker="o", linestyle="--", label=f"{arch} spawn")
                ax.plot(x.delay_ms, x.drain_time_ms, marker="s", label=f"{arch} drain")
        ax.set_title(f"Spawn schedule time vs post-spawn drain time {'(10 KB payload)' if payload else '(no payload)'}")
        ax.set_xlabel("Inter-instance delay (ms)")
        ax.set_ylabel("Time (ms)")
        ax.axhline(DRAIN_NOISE_FLOOR_MS, linestyle=":", linewidth=1, label="2 s measurement floor")
        ax.invert_xaxis()
        ax.legend(ncol=2)
        save(fig, out, f"02_spawn_drain_{'payload' if payload else 'plain'}.png")


def plot_drain_share(df, out):
    d = df.copy()
    #d["drain_share_pct"] = 100 * d.drain_time_ms / d.total_time_ms
    d["drain_share_pct"] = d.drain_time_ms
    #d["effective_drain_share_pct"] = 100 * d.effective_drain_ms / d.total_time_ms
    for payload in [False, True]:
        fig, ax = plt.subplots()
        for arch in ARCH_ORDER:
            x = d[(d.architecture == arch) & (d.payload == payload)].sort_values("delay_ms")
            if not x.empty:
                ax.plot(x.delay_ms, x.drain_share_pct, marker="o", label=arch)
        ax.set_title(f"Post-spawn drain / overload indicator {'(10 KB payload)' if payload else '(no payload)'}")
        ax.set_xlabel("Inter-instance delay (ms)")
        ax.set_ylabel("Drain duration (ms)")
        ax.set_yscale('log')

        ax.invert_xaxis()
        ax.set_ylim(bottom=0)
        #ax.yaxis.set_major_formatter(ScalarFormatter())
        ax.legend()
        save(fig, out, f"03_drain_share_{'payload' if payload else 'plain'}.png")


def plot_latency(df, out):
    for delay_ms in DELAYS_MS:
        for payload in [False, True]:
            sub = df[(df.delay_ms == delay_ms) & (df.payload == payload)].copy()
            if sub.empty:
                continue
            x = np.arange(len(sub))
            width = 0.18
            fig, ax = plt.subplots(figsize=(11, 6))
            for i, metric in enumerate(PERCENTILES):
                ax.bar(x + (i - 1.5) * width, sub[f"{metric}_ms"], width, label=metric)
            ax.set_xticks(x)
            ax.set_xticklabels(sub.architecture)
            ax.set_yscale("log")
            ax.set_title(f"Process-instance lifetime percentiles — {delay_ms} ms inter-instance delay {'(10 KB payload)' if payload else '(no payload)'}")
            ax.set_xlabel("Architecture")
            ax.set_ylabel("Lifetime (ms, log scale)")
            ax.legend()
            save(fig, out, f"04_latency_delay{delay_ms}_{'payload' if payload else 'plain'}.png")


def plot_payload_effect(df, out):
    rows = []
    for arch in ARCH_ORDER:
        for delay_ms in DELAYS_MS:
            plain = df[(df.architecture == arch) & (df.delay_ms == delay_ms) & (~df.payload)]
            payload = df[(df.architecture == arch) & (df.delay_ms == delay_ms) & (df.payload)]
            if plain.empty or payload.empty:
                continue
            p, q = plain.iloc[0], payload.iloc[0]
            rows.append({
                "architecture": arch,
                "delay_ms": delay_ms,
                "tx_multiplier": q.tx_bytes_per_instance / p.tx_bytes_per_instance,
                "rx_multiplier": q.rx_bytes_per_instance / p.rx_bytes_per_instance,
                "total_time_change_pct": pct_change(q.total_time_ms, p.total_time_ms),
                "p99_change_pct": pct_change(q.p99_ms, p.p99_ms),
            })
    ov = pd.DataFrame(rows)
    if ov.empty:
        return

    for value, title, ylabel, filename in [
        ("tx_multiplier", "10 KB payload effect on network TX", "Payload / plain TX bytes per instance", "05_payload_tx_multiplier.png"),
        ("total_time_change_pct", "10 KB payload effect on total test duration", "Change vs plain (%)", "06_payload_total_time_change.png"),
        ("p99_change_pct", "10 KB payload effect on p99 lifetime", "Change vs plain (%)", "07_payload_p99_change.png"),
    ]:
        fig, ax = plt.subplots()
        for arch in ARCH_ORDER:
            x = ov[ov.architecture == arch].sort_values("delay_ms")
            if not x.empty:
                ax.plot(x.delay_ms, x[value], marker="o", label=arch)
        baseline = 1.0 if "multiplier" in value else 0.0
        ax.axhline(baseline, linewidth=1)
        ax.set_title(title)
        ax.set_xlabel("Inter-instance delay (ms)")
        ax.set_ylabel(ylabel)
        ax.invert_xaxis()
        ax.legend()
        save(fig, out, filename)


def plot_network(df, out):
    for payload in [False, True]:
        fig, ax = plt.subplots()
        for arch in ARCH_ORDER:
            x = series(df, arch, payload)
            if not x.empty:
                ax.plot(x.delay_ms, x.tx_bytes_per_instance, marker="o", label=arch)
        ax.set_title(f"Average TX bytes per process instance {'(10 KB payload)' if payload else '(no payload)'}")
        ax.set_xlabel("Inter-instance delay (ms)")
        ax.set_ylabel("TX bytes per instance")
        ax.invert_xaxis()
        ax.legend()
        save(fig, out, f"08_network_tx_{'payload' if payload else 'plain'}.png")


def make_summary(df, config=None):
    lines = [
        "Process-engine architecture benchmark analysis",
        "=" * 45,
        "",
        "Interpretation: c5000-X means 5000 process instances with X ms between instance starts. "
        "The -payload cases use a 10,000-byte instance payload. All measured times are milliseconds.",
        f"Measurement semantics: total = test start to end of the last instance; spawn = test start to end of spawning; drain = end of spawning until all instances are processed. Drain below {DRAIN_NOISE_FLOOR_MS} ms is effectively zero for this measurement setup.",
        "A drain above the measurement floor means processing is still outstanding after spawning has stopped; for a sustained arrival rate, this is evidence of backlog/overload.",
        "Repetitions are aggregated by arithmetic mean; reported latency percentiles are therefore means of per-run percentiles.",
        "",
    ]
    if config:
        lines.append(f"Configuration repeats: {config.get('repeats', 'unknown')}")
        lines.append("")

    lines.append("Total test duration by architecture and inter-instance delay")
    for payload in [False, True]:
        lines.append(f"  {'10 KB payload' if payload else 'no payload'}")
        sub = df[df.payload == payload]
        for delay_ms in DELAYS_MS:
            x = sub[sub.delay_ms == delay_ms].sort_values("total_time_ms")
            if not x.empty:
                vals = ", ".join(f"{r.architecture}={r.total_time_ms:.0f} ms" for _, r in x.iterrows())
                lines.append(f"    {delay_ms:>3} ms: {vals}")
    lines.append("")

    d = df.copy()
    d["drain_share_pct"] = 100 * d.drain_time_ms / d.total_time_ms
    lines.append(f"Overload/backlog cases (drain >= {DRAIN_NOISE_FLOOR_MS} ms)")
    od = d[d.drain_time_ms >= DRAIN_NOISE_FLOOR_MS].sort_values(["delay_ms", "drain_time_ms"], ascending=[True, False])
    if od.empty:
        lines.append("  none")
    else:
        for _, r in od.iterrows():
            lines.append(f"  {r.architecture:5s} {r.testcase:18s}: drain={r.drain_time_ms:.0f} ms, total={r.total_time_ms:.0f} ms")
    lines.append("")

    lines.append("Raw drain-share extremes")
    for _, r in d.sort_values("drain_share_pct", ascending=False).head(8).iterrows():
        lines.append(f"  {r.architecture:5s} {r.testcase:18s}: {r.drain_share_pct:.1f}% drain ({r.drain_time_ms:.0f} / {r.total_time_ms:.0f} ms)")
    lines.append("")

    lines.append("p99 lifetime comparison: poll relative to each other architecture")
    for delay_ms in DELAYS_MS:
        for payload in [False, True]:
            sub = df[(df.delay_ms == delay_ms) & (df.payload == payload)].set_index("architecture")
            if "poll" not in sub.index:
                continue
            parts = []
            for arch in ["push", "amqp", "s3"]:
                if arch in sub.index and sub.loc[arch, "p99_ms"] > 0:
                    parts.append(f"poll/{arch}={sub.loc['poll', 'p99_ms']/sub.loc[arch, 'p99_ms']:.1f}x")
            lines.append(f"  {delay_ms:>3} ms, {'payload' if payload else 'plain'}: " + ", ".join(parts))
    lines.append("")

    lines.append("Payload network TX multiplier (10 KB payload / plain)")
    for arch in ARCH_ORDER:
        parts = []
        for delay_ms in DELAYS_MS:
            p = df[(df.architecture == arch) & (df.delay_ms == delay_ms) & (~df.payload)]
            q = df[(df.architecture == arch) & (df.delay_ms == delay_ms) & (df.payload)]
            if not p.empty and not q.empty:
                parts.append(f"{delay_ms}ms={q.iloc[0].tx_bytes_per_instance/p.iloc[0].tx_bytes_per_instance:.2f}x")
        lines.append(f"  {arch}: " + ", ".join(parts))
    
    lines.append("Payload network TX cost per byte of payload")
    for arch in ARCH_ORDER:
        parts = []
        for delay_ms in DELAYS_MS:
            p = df[(df.architecture == arch) & (df.delay_ms == delay_ms) & (~df.payload)]
            q = df[(df.architecture == arch) & (df.delay_ms == delay_ms) & (df.payload)]
            if not p.empty and not q.empty:
                parts.append(f"{delay_ms}ms={(p.iloc[0].tx_bytes_per_instance-q.iloc[0].tx_bytes_per_instance)/10000:.2f}x")
        lines.append(f"  {arch}: " + ", ".join(parts))
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="measurement JSON")
    parser.add_argument("--config", type=Path, default=None, help="testcase JSON/JSONC configuration")
    parser.add_argument("-o", "--output", type=Path, default=Path("architecture_analysis"))
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)
    results = load_json(args.input)
    config = load_config(args.config)
    df = aggregate(results)
    df.to_csv(args.output / "aggregated_metrics.csv", index=False)

    setup()
    plot_total_duration(df, args.output)
    plot_spawn_drain(df, args.output)
    plot_drain_share(df, args.output)
    plot_latency(df, args.output)
    plot_payload_effect(df, args.output)
    plot_network(df, args.output)
    (args.output / "summary.txt").write_text(make_summary(df, config), encoding="utf-8")
    print(f"Wrote analysis to {args.output.resolve()}")


if __name__ == "__main__":
    main()
