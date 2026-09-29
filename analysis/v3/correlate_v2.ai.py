"""
Correlate benchmark runs with their scratch instance logs and publish
deterministic per-tag aggregates.

Pipeline
--------
For each ``data/raw/raw-<timestamp>-<tag>.json`` run:

1. Load the raw testcase JSON.
2. For each testcase, locate the nearest ``data/scratch/<timestamp>.txt``
   within ``SCRATCH_MATCH_MARGIN_MS`` of the raw testcase's ``timing.end_test``.
3. Read ``start,end,duration`` instance observations.
4. Preserve the original per-run semantics:
   - sort start/end timestamps;
   - replace ``timing.end_test`` with the latest actual instance end;
   - compute lifetime, start-delta, and end-delta distribution statistics;
   - compute spawn/completion rates from mean inter-event intervals.

Runs are then grouped independently by filename tag.  Within a tag, testcases
are grouped by a deterministic serialization of their complete ``config``
object, never by ``testId``.

For each configuration:
- duration/start-delta/end-delta observations are pooled across runs and exact
  pooled distribution statistics are calculated;
- throughput is calculated from pooled inter-event intervals, not averaged
  from per-run rates;
- run-level means are retained and summarized with a Student-t confidence
  interval.  Runs are the independent units for this uncertainty calculation.

The output is deterministic: filesystem ordering is never used as an input to
ordering, tags come from filenames, scratch logs are matched by nearest
timestamp, configurations are sorted by canonical JSON, and aggregate
testIds are assigned sequentially after sorting.

The confidence interval is for the mean of the run-level measurements, not
for individual instances.  ``confidence`` is configurable and SciPy's
Student-t quantile is used directly; no hard-coded critical-value table is
used.

For published datasets, pin compatible NumPy/SciPy versions in the project's
dependency/lock file.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any, Iterable

import numpy as np
from scipy.stats import t


RAW_PATTERN = re.compile(r"^raw-(?P<timestamp>\d+)-(?P<tag>.+)\.json$")
DEFAULT_RAW_DIR = Path("data/raw")
DEFAULT_SCRATCH_DIR = Path("data/scratch")
DEFAULT_CORRELATED_DIR = Path("data/processed/correlated")
DEFAULT_AGGREGATED_DIR = Path("data/processed/aggregated")
SCRATCH_MATCH_MARGIN_MS = 5000


def statistics_from_stream(data: Iterable[float | int]) -> dict[str, Any]:
    """Return the original distribution statistics for a non-empty stream."""
    values = np.asarray(list(data))
    if values.size == 0:
        raise ValueError("Cannot calculate statistics for an empty stream.")

    return {
        "count": int(values.size),
        "min": int(np.min(values)),
        "max": int(np.max(values)),
        "mean": float(np.mean(values)),
        "std_dev": float(np.std(values)),
        "p50": float(np.percentile(values, 50)),
        "p90": float(np.percentile(values, 90)),
        "p95": float(np.percentile(values, 95)),
        "p99": float(np.percentile(values, 99)),
    }


def canonical_config(config: Any) -> str:
    """Serialize a config deterministically for cross-run grouping."""
    return json.dumps(config, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def get_raw_runs(raw_dir: Path) -> list[tuple[str, int, Path]]:
    """Return ``(tag, run_timestamp, path)`` sorted deterministically."""
    runs: list[tuple[str, int, Path]] = []

    for path in sorted(raw_dir.glob("*.json"), key=lambda p: p.name):
        match = RAW_PATTERN.fullmatch(path.name)
        if not match:
            continue
        runs.append((match.group("tag"), int(match.group("timestamp")), path))

    return sorted(runs, key=lambda item: (item[0], item[1], item[2].name))


def get_scratch_logs(scratch_dir: Path) -> list[tuple[int, Path]]:
    """Return scratch logs whose filenames are numeric timestamps."""
    logs = []
    for path in scratch_dir.glob("*.txt"):
        try:
            timestamp = int(path.stem)
        except ValueError:
            continue
        logs.append((timestamp, path))
    return sorted(logs, key=lambda item: (item[0], item[1].name))


def get_instance_log_name(
    target_time: int,
    basepath: Path | str = DEFAULT_SCRATCH_DIR,
    margin: int = SCRATCH_MATCH_MARGIN_MS,
) -> Path | None:
    """Return the nearest scratch log within ``margin`` milliseconds."""
    scratch_dir = Path(basepath)
    candidates = get_scratch_logs(scratch_dir)
    if not candidates:
        return None

    nearest = min(candidates, key=lambda item: (abs(item[0] - target_time), item[0], item[1].name))
    if abs(nearest[0] - target_time) >= margin:
        return None
    return nearest[1]


def read_instance_log(path: Path) -> list[dict[str, int]]:
    """Read a headerless ``start,end,duration`` scratch log."""
    instances: list[dict[str, int]] = []

    with path.open() as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue

            fields = stripped.split(",")
            if len(fields) != 3:
                raise ValueError(
                    f"{path}:{line_number}: expected start,end,duration, got {len(fields)} fields"
                )

            try:
                start, end, duration = (int(field) for field in fields)
            except ValueError as exc:
                raise ValueError(
                    f"{path}:{line_number}: start/end/duration must be integers"
                ) from exc

            instances.append({"start": start, "end": end, "duration": duration})

    if not instances:
        raise ValueError(f"Scratch log is empty: {path}")

    return instances


def correlate_testcase(
    testcase: dict[str, Any],
    scratch_dir: Path,
    scratch_margin_ms: int,
) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    """Hydrate one testcase and return it plus raw streams for aggregation."""
    timing = testcase.get("timing")
    if not isinstance(timing, dict) or timing.get("end_test") is None:
        raise ValueError("Testcase is missing timing.end_test")

    original_end_test = int(timing["end_test"])
    scratch_path = get_instance_log_name(
        original_end_test,
        basepath=scratch_dir,
        margin=scratch_margin_ms,
    )
    if scratch_path is None:
        raise FileNotFoundError(
            f"No scratch log within {scratch_margin_ms} ms of testcase end_test "
            f"{original_end_test}"
        )

    instances = read_instance_log(scratch_path)

    start_times = np.asarray([instance["start"] for instance in instances], dtype=np.int64)
    end_times = np.asarray([instance["end"] for instance in instances], dtype=np.int64)
    durations = np.asarray([instance["duration"] for instance in instances], dtype=np.int64)

    start_times.sort()
    end_times.sort()

    start_deltas = np.diff(start_times)
    end_deltas = np.diff(end_times)

    # The original implementation assumes repeated instances, so delta
    # streams are non-empty. Fail clearly instead of emitting NaN/inf.
    if start_deltas.size == 0 or end_deltas.size == 0:
        raise ValueError(
            f"Scratch log {scratch_path} must contain at least two instances "
            "to calculate start/end deltas."
        )

    testcase = json.loads(json.dumps(testcase))
    testcase["timing"]["end_test"] = int(end_times[-1])
    testcase["instance_statistics"] = {
        "lifetime": statistics_from_stream(durations),
        "start_deltas": statistics_from_stream(start_deltas),
        "end_deltas": statistics_from_stream(end_deltas),
        "spawns": {
            "avg_spawns_per_second": float(1000 / np.mean(start_deltas)),
            "avg_completes_per_second": float(1000 / np.mean(end_deltas)),
        },
    }

    streams = {
        "duration": durations,
        "start_deltas": start_deltas,
        "end_deltas": end_deltas,
    }
    return testcase, streams


def correlate_from_raw_log(
    path: Path | str,
    scratch_dir: Path | str = DEFAULT_SCRATCH_DIR,
    scratch_margin_ms: int = SCRATCH_MATCH_MARGIN_MS,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Correlate a raw run and retain raw streams for later pooling."""
    raw_path = Path(path)
    with raw_path.open() as handle:
        raw_log = json.load(handle)

    if not isinstance(raw_log, list):
        raise ValueError(f"Expected testcase list in {raw_path}")

    correlated: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []

    for testcase in raw_log:
        if not isinstance(testcase, dict):
            raise ValueError(f"Expected testcase object in {raw_path}")

        hydrated, streams = correlate_testcase(
            testcase,
            Path(scratch_dir),
            scratch_margin_ms,
        )
        correlated.append(hydrated)
        records.append({"testcase": hydrated, "streams": streams})

    return correlated, records


def run_level_summary(values: Iterable[float | int], confidence: float) -> dict[str, Any]:
    """Summarize independent run-level measurements with a Student-t CI."""
    values_array = np.asarray(list(values), dtype=float)
    n = int(values_array.size)
    if n == 0:
        raise ValueError("Cannot summarize zero run-level measurements.")

    mean = float(np.mean(values_array))

    if n == 1:
        sample_std = 0.0
        critical = None
        margin = 0.0
        ci_low = mean
        ci_high = mean
    else:
        sample_std = float(np.std(values_array, ddof=1))
        critical = float(t.ppf(1 - (1 - confidence) / 2, df=n - 1))
        margin = float(critical * sample_std / math.sqrt(n))
        ci_low = mean - margin
        ci_high = mean + margin

    return {
        "n_runs": n,
        "mean": mean,
        "sample_std_dev": sample_std,
        "confidence": confidence,
        "critical_value": critical,
        "margin": margin,
        "ci_low": float(ci_low),
        "ci_high": float(ci_high),
        "measurements": [float(value) for value in values_array],
    }


def pooled_distribution(
    streams: Iterable[np.ndarray],
) -> dict[str, Any]:
    """Pool individual observations from all runs and calculate exact stats."""
    arrays = [np.asarray(stream) for stream in streams]
    if not arrays:
        raise ValueError("No streams supplied for pooling.")
    pooled = np.concatenate(arrays)
    return statistics_from_stream(pooled)


def aggregate_configuration(
    config: Any,
    run_records: list[dict[str, Any]],
    confidence: float,
) -> dict[str, Any]:
    """Build one aggregate testcase from equivalent configurations."""
    duration_streams = [record["streams"]["duration"] for record in run_records]
    start_delta_streams = [record["streams"]["start_deltas"] for record in run_records]
    end_delta_streams = [record["streams"]["end_deltas"] for record in run_records]

    pooled_start = np.concatenate(start_delta_streams)
    pooled_end = np.concatenate(end_delta_streams)

    # Run-level aggregate measurements. These are retained separately from
    # pooled observations because runs are the independent units for CI.
    run_duration_means = [
        float(np.mean(record["streams"]["duration"])) for record in run_records
    ]
    run_start_delta_means = [
        float(np.mean(record["streams"]["start_deltas"])) for record in run_records
    ]
    run_end_delta_means = [
        float(np.mean(record["streams"]["end_deltas"])) for record in run_records
    ]
    run_spawn_rates = [float(1000 / value) for value in run_start_delta_means]
    run_completion_rates = [float(1000 / value) for value in run_end_delta_means]

    return {
        "config": config,
        "instance_statistics": {
            "lifetime": {
                **pooled_distribution(duration_streams),
                "run_level_mean": run_level_summary(run_duration_means, confidence),
            },
            "start_deltas": {
                **pooled_distribution(start_delta_streams),
                "run_level_mean": run_level_summary(run_start_delta_means, confidence),
            },
            "end_deltas": {
                **pooled_distribution(end_delta_streams),
                "run_level_mean": run_level_summary(run_end_delta_means, confidence),
            },
            "spawns": {
                "avg_spawns_per_second": float(1000 / np.mean(pooled_start)),
                "avg_completes_per_second": float(1000 / np.mean(pooled_end)),
                "run_level_avg_spawns_per_second": run_level_summary(
                    run_spawn_rates, confidence
                ),
                "run_level_avg_completes_per_second": run_level_summary(
                    run_completion_rates, confidence
                ),
            },
        },
        "run_count": len(run_records),
        "run_timestamps": sorted(record["run_timestamp"] for record in run_records),
    }


def aggregate_tag(
    tag: str,
    correlated_runs: list[tuple[int, str, list[dict[str, Any]], list[dict[str, Any]]]],
    confidence: float,
) -> list[dict[str, Any]]:
    """Aggregate all correlated runs belonging to exactly one tag."""
    groups: dict[str, list[dict[str, Any]]] = {}

    for run_timestamp, filename, correlated, records in correlated_runs:
        for testcase, record in zip(correlated, records):
            if "config" not in testcase:
                raise ValueError(f"{filename}: testcase is missing config")

            key = canonical_config(testcase["config"])
            groups.setdefault(key, []).append(
                {
                    "run_timestamp": run_timestamp,
                    "filename": filename,
                    "streams": record["streams"],
                }
            )

    aggregate_testcases = []
    for config_key in sorted(groups):
        run_records = groups[config_key]
        config = json.loads(config_key)
        aggregate_testcases.append(
            aggregate_configuration(config, run_records, confidence)
        )

    for test_id, testcase in enumerate(aggregate_testcases):
        testcase["testId"] = test_id

    return aggregate_testcases


def process(
    raw_dir: Path = DEFAULT_RAW_DIR,
    scratch_dir: Path = DEFAULT_SCRATCH_DIR,
    correlated_dir: Path = DEFAULT_CORRELATED_DIR,
    aggregated_dir: Path = DEFAULT_AGGREGATED_DIR,
    scratch_margin_ms: int = SCRATCH_MATCH_MARGIN_MS,
    confidence: float = 0.95,
) -> None:
    """Run the complete deterministic per-tag correlation/aggregation pipeline."""
    if not 0 < confidence < 1:
        raise ValueError("confidence must be strictly between 0 and 1")

    raw_runs = get_raw_runs(raw_dir)
    if not raw_runs:
        raise FileNotFoundError(f"No raw runs matching raw-<timestamp>-<tag>.json in {raw_dir}")

    correlated_dir.mkdir(parents=True, exist_ok=True)
    aggregated_dir.mkdir(parents=True, exist_ok=True)

    by_tag: dict[str, list[tuple[int, str, list[dict[str, Any]], list[dict[str, Any]]]]] = {}

    for index, (tag, run_timestamp, raw_path) in enumerate(raw_runs, start=1):
        print(f"{index}/{len(raw_runs)} {raw_path.name}")

        correlated, records = correlate_from_raw_log(
            raw_path,
            scratch_dir=scratch_dir,
            scratch_margin_ms=scratch_margin_ms,
        )

        tag_dir = correlated_dir / tag
        tag_dir.mkdir(parents=True, exist_ok=True)
        output_path = tag_dir / raw_path.name
        with output_path.open("w") as outfile:
            json.dump(correlated, outfile, indent=4, sort_keys=False)
            outfile.write("\n")

        by_tag.setdefault(tag, []).append(
            (run_timestamp, raw_path.name, correlated, records)
        )

    for tag in sorted(by_tag):
        aggregate = aggregate_tag(tag, by_tag[tag], confidence)
        output = {
            "tag": tag,
            "methodology": {
                "grouping": "canonical JSON serialization of complete config",
                "pooling": "individual observations pooled across runs",
                "throughput": "1000 / pooled mean inter-event interval",
                "run_uncertainty": {
                    "independent_unit": "run",
                    "confidence": confidence,
                    "distribution": "Student-t",
                    "sample_standard_deviation_ddof": 1,
                    "ci": "two-sided confidence interval for run-level mean",
                },
            },
            "testcases": aggregate,
        }

        output_path = aggregated_dir / f"{tag}.json"
        with output_path.open("w") as outfile:
            json.dump(output, outfile, indent=4, sort_keys=False)
            outfile.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument("--scratch-dir", type=Path, default=DEFAULT_SCRATCH_DIR)
    parser.add_argument("--correlated-dir", type=Path, default=DEFAULT_CORRELATED_DIR)
    parser.add_argument("--aggregated-dir", type=Path, default=DEFAULT_AGGREGATED_DIR)
    parser.add_argument("--scratch-margin-ms", type=int, default=SCRATCH_MATCH_MARGIN_MS)
    parser.add_argument("--confidence", type=float, default=0.95)
    args = parser.parse_args()

    process(
        raw_dir=args.raw_dir,
        scratch_dir=args.scratch_dir,
        correlated_dir=args.correlated_dir,
        aggregated_dir=args.aggregated_dir,
        scratch_margin_ms=args.scratch_margin_ms,
        confidence=args.confidence,
    )


if __name__ == "__main__":
    main()
