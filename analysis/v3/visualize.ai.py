import json, os, math
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import ScalarFormatter
from matplotlib.backends.backend_pdf import PdfPages

base = "data/results"
base_in = "data/processed/aggregated"

ARCHITECTURE_TAGS = [
    "push",
    "poll",
    "s3",
    "amqp"
]

files = {
    "push": f"{base_in}/push.json",
    "poll": f"{base_in}/poll.json",
    "s3": f"{base_in}/s3.json",
    "amqp": f"{base_in}/amqp.json"
}
datasets = {}
for tag, path in files.items():
    with open(path, "r") as f:
        datasets[tag] = json.load(f)

def rows_for(tag):
    out = []
    for tc in datasets[tag]["testcases"]:
        c = tc["config"]
        s = tc["instance_statistics"]
        sp = s["spawns"]
        life = s["lifetime"]
        ci_sp = sp["run_level_avg_spawns_per_second"]
        ci_co = sp["run_level_avg_completes_per_second"]
        out.append({
            "tag": tag,
            "label": c["label"],
            "delay_ms": c["delayMs"],
            "payload_bytes": c["instanceConfig"]["payloadSize"],
            "instance_count": c["instanceCount"],
            "spawn_rate": sp["avg_spawns_per_second"],
            "complete_rate": sp["avg_completes_per_second"],
            "spawn_ci_low": ci_sp["ci_low"],
            "spawn_ci_high": ci_sp["ci_high"],
            "complete_ci_low": ci_co["ci_low"],
            "complete_ci_high": ci_co["ci_high"],
            "p50": life["p50"],
            "p95": life["p95"],
            "p99": life["p99"],
            "lifetime_mean": life["mean"],
            "n_runs": ci_sp["n_runs"],
        })
    return pd.DataFrame(out).sort_values(["delay_ms", "payload_bytes"]).reset_index(drop=True)

df = pd.concat([
    rows_for("push"),
    rows_for("poll"),
    rows_for("s3"),
    rows_for("amqp")
], ignore_index=True)

# 1. Per-architecture throughput figures: log y is explicit because rates span ~2 orders of magnitude.
throughput_paths = []
for tag in ARCHITECTURE_TAGS:
    sub = df[df.tag == tag]
    fig, ax = plt.subplots(figsize=(10.5, 6.0))
    for payload, marker in [(0, "o"), (10000, "s")]:
        d = sub[sub.payload_bytes == payload].sort_values("delay_ms")
        x = d.delay_ms.to_numpy()
        y = d.complete_rate.to_numpy()
        lo = d.complete_ci_low.to_numpy()
        hi = d.complete_ci_high.to_numpy()
        label = "payload=0" if payload == 0 else "payload=10,000 B"
        ax.errorbar(x, y, yerr=[y-lo, hi-y], marker=marker, linewidth=2,
                    capsize=3, label=label)
        # Spawn rate is plotted as a light secondary marker on the same scale to retain both required metrics.
        ys = d.spawn_rate.to_numpy()
        ax.plot(x, ys, marker=marker, linestyle="--", alpha=0.65,
                label=f"{label}, spawn")
    ax.set_yscale("log")
    ax.set_xlabel("Configured delay (ms)")
    ax.set_ylabel("Throughput (instances/s, log scale)")
    ax.set_title(f"{tag.capitalize()} — throughput by configuration")
    ax.set_xticks(sorted(sub.delay_ms.unique()))
    ax.grid(True, which="major", axis="y", alpha=0.25)
    ax.grid(True, which="minor", axis="y", alpha=0.10)
    ax.legend(ncol=2, fontsize=9)
    ax.text(0.01, -0.18,
            "Solid = completion throughput; dashed = spawn throughput. Error bars are 95% run-level CIs for completion throughput.",
            transform=ax.transAxes, fontsize=8.5)
    fig.tight_layout()
    p = f"{base}/{tag}_throughput.png"
    fig.savefig(p, dpi=180, bbox_inches="tight")
    throughput_paths.append(p)
    plt.close(fig)

# 2. Per-architecture lifetime percentile plots.
lifetime_paths = []
for tag in ARCHITECTURE_TAGS:
    sub = df[df.tag == tag].copy()
    fig, ax = plt.subplots(figsize=(11.0, 6.2))
    # Use x positions grouped by delay, with payload offsets.
    delays = sorted(sub.delay_ms.unique())
    x0 = np.arange(len(delays))
    offsets = {-1: -0.14, 1: 0.14}
    for payload, off, marker in [(0, -0.14, "o"), (10000, 0.14, "s")]:
        d = sub[sub.payload_bytes == payload].set_index("delay_ms").loc[delays]
        x = x0 + off
        label = "payload=0" if payload == 0 else "payload=10,000 B"
        ax.plot(x, d.p50, marker=marker, linewidth=1.8, label=f"{label}: p50")
        ax.plot(x, d.p95, marker=marker, linewidth=1.8, linestyle="--", label=f"{label}: p95")
        ax.plot(x, d.p99, marker=marker, linewidth=1.8, linestyle=":", label=f"{label}: p99")
    ax.set_yscale("log")
    ax.set_xticks(x0)
    ax.set_xticklabels([str(v) for v in delays])
    ax.set_xlabel("Configured delay (ms)")
    ax.set_ylabel("Instance lifetime (source units, log scale)")
    ax.set_title(f"{tag.capitalize()} — pooled lifetime percentiles")
    ax.grid(True, which="major", axis="y", alpha=0.25)
    ax.grid(True, which="minor", axis="y", alpha=0.10)
    ax.legend(ncol=2, fontsize=8.5)
    ax.text(0.01, -0.17,
            "Pooled instance percentiles; not confidence intervals. p50, p95 and p99 are shown as specified by the reporting handoff.",
            transform=ax.transAxes, fontsize=8.5)
    fig.tight_layout()
    p = f"{base}/{tag}_lifetime_percentiles.png"
    fig.savefig(p, dpi=180, bbox_inches="tight")
    lifetime_paths.append(p)
    plt.close(fig)

# 3. Cross-architecture completion throughput comparison.
comp_path = f"{base}/architecture_completion_throughput.png"
fig, ax = plt.subplots(figsize=(11.5, 6.3))
delays = sorted(df.delay_ms.unique())
x = np.arange(len(delays))
width = 0.18
positions = []
for i, (payload, payload_label) in enumerate([(0, "payload=0"), (10000, "payload=10,000 B")]):
    for j, tag in enumerate(ARCHITECTURE_TAGS):
        d = df[(df.tag == tag) & (df.payload_bytes == payload)].set_index("delay_ms").loc[delays]
        pos = x + (i*2+j - 1.5)*width
        positions.append(pos)
        y = d.complete_rate.to_numpy()
        lo = d.complete_ci_low.to_numpy()
        hi = d.complete_ci_high.to_numpy()
        ax.bar(pos, y, width=width, label=f"{tag}, {payload_label}")
        ax.errorbar(pos, y, yerr=[y-lo, hi-y], fmt="none", ecolor="black", capsize=2, linewidth=0.8)
ax.set_yscale("log")
ax.set_xticks(x)
ax.set_xticklabels([f"{d} ms" for d in delays])
ax.set_xlabel("Configured delay")
ax.set_ylabel("Completion throughput (instances/s, log scale)")
ax.set_title("Push vs poll — completion throughput under equivalent configurations")
ax.grid(True, which="major", axis="y", alpha=0.25)
ax.grid(True, which="minor", axis="y", alpha=0.10)
ax.legend(ncol=2, fontsize=8.5)
ax.text(0.01, -0.17,
        "Same configuration grid and y-axis semantics across architectures. Error bars are 95% run-level CIs (n=7 push; n=11 poll).",
        transform=ax.transAxes, fontsize=8.5)
fig.tight_layout()
fig.savefig(comp_path, dpi=180, bbox_inches="tight")
plt.close(fig)

# 4. Cross-architecture p95 lifetime comparison.
tail_path = f"{base}/architecture_p95_lifetime.png"
fig, ax = plt.subplots(figsize=(11.5, 6.3))
for i, (payload, payload_label) in enumerate([(0, "payload=0"), (10000, "payload=10,000 B")]):
    for j, tag in enumerate(ARCHITECTURE_TAGS):
        d = df[(df.tag == tag) & (df.payload_bytes == payload)].set_index("delay_ms").loc[delays]
        pos = x + (i*2+j - 1.5)*width
        ax.bar(pos, d.p95.to_numpy(), width=width, label=f"{tag}, {payload_label}")
ax.set_yscale("log")
ax.set_xticks(x)
ax.set_xticklabels([f"{d} ms" for d in delays])
ax.set_xlabel("Configured delay")
ax.set_ylabel("P95 instance lifetime (source units, log scale)")
ax.set_title("Push vs poll — p95 lifetime under equivalent configurations")
ax.grid(True, which="major", axis="y", alpha=0.25)
ax.grid(True, which="minor", axis="y", alpha=0.10)
ax.legend(ncol=2, fontsize=8.5)
ax.text(0.01, -0.17,
        "P95 is a pooled-instance percentile; it is not a run-level confidence interval.",
        transform=ax.transAxes, fontsize=8.5)
fig.tight_layout()
fig.savefig(tail_path, dpi=180, bbox_inches="tight")
plt.close(fig)

# Create a compact PDF containing the four figures.
pdf_path = f"{base}/benchmark_visualizations.pdf"
with PdfPages(pdf_path) as pdf:
    for p in throughput_paths + lifetime_paths + [comp_path, tail_path]:
        img = plt.imread(p)
        fig, ax = plt.subplots(figsize=(11.5, 6.5))
        ax.imshow(img)
        ax.axis("off")
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

# Machine-readable plotting table for reproducibility.
csv_path = f"{base}/benchmark_plot_data.csv"
df.to_csv(csv_path, index=False)

print("Created:")
for p in throughput_paths + lifetime_paths + [comp_path, tail_path, pdf_path, csv_path]:
    print(p)
