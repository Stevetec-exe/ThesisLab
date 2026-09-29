import json
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

src = Path("data/processed/results-1789716151959.json")
out = Path("out.png")

with src.open() as f:
    data = json.load(f)

architectures = ["push", "poll", "amqp", "s3"]
delays = [100, 50, 25, 10, 0]

metrics = {}
for arch in architectures:
    for delay in delays:
        reps = data[arch][f"c5000-{delay}-payload"]
        metrics[(arch, delay)] = {
            p: float(np.mean([r["lifetimes"][p] for r in reps]))
            for p in ["p50", "p90", "p95", "p99"]
        }

fig, axes = plt.subplots(1, 5, figsize=(16, 5.8))
x = np.arange(len(architectures))

for ax, delay in zip(axes, delays):
    for i, arch in enumerate(architectures):
        v = metrics[(arch, delay)]
        ax.vlines(i, v["p50"], v["p99"], linewidth=2)
        ax.scatter(i, v["p50"], s=48, zorder=3)
        for p, size in [("p90", 22), ("p95", 28), ("p99", 34)]:
            ax.scatter(i, v[p], s=size, marker="_", linewidths=2.4, zorder=3)

    ax.set_xticks(x)
    ax.set_xticklabels(architectures)
    ax.set_title(f"{delay} ms spawn delay")
    ax.set_yscale("linear")
    ax.set_ylim(bottom=1)
    ax.grid(axis="y", alpha=0.25)
    if ax is axes[0]:
        ax.set_ylabel("Instance lifetime (ms)")

fig.suptitle("Instance lifetime percentiles by architecture and spawn delay (with 10kb payload)", fontsize=14)
fig.text(
    0.5, 0.01,
    "Dot = p50; short ticks = p90, p95, p99. Values are arithmetic means across the 3 repetitions. Log scale.",
    ha="center", fontsize=10
)
fig.tight_layout(rect=[0, 0.04, 1, 0.96])
fig.savefig(out, dpi=220, bbox_inches="tight")
plt.show()

print(f"Saved to: {out}")
