"""Render descriptive statistics from the timed CSV rows without pooling arms or passes."""
import csv
from collections import defaultdict
from pathlib import Path
from statistics import geometric_mean, mean, stdev

ROOT = Path(__file__).resolve().parents[2]
GROUPS = [
    ("decode_heavy", "", "Decode TPOT", "ms/token", "median_tpot_ms"),
    ("prefill_heavy", "", "Prefill TTFT", "ms", "median_ttft_ms"),
    *(("high_load", f"c{n}", f"High load c{n}", "requests/s", "request_throughput") for n in (16, 32, 64)),
]


def render():
    lines = [
        "# Variation across timed repetitions",
        "",
        "Each row describes one arm of one public benchmark pass on two A100s. "
        "Decode uses each repetition’s median time per output token (TPOT). "
        "Prefill uses each repetition’s median time to first token (TTFT). "
        "High load uses each profile’s completed requests per second. "
        "The combined high-load row takes the geometric mean across the three concurrencies "
        "within each repetition before summarizing across repetitions.",
        "",
        "The mean, minimum, maximum and sample standard deviation (SD, denominator n − 1) "
        "use all repetitions, before score trimming. Values are rounded to five decimal places. "
        "A single observation gives no estimate of between-repetition variation. "
        "Two decode boots or two high-load repetitions provide only one degree of freedom. "
        "These samples describe this run on this device pair. They cannot establish "
        "campaign-to-campaign variation or a general noise floor.",
    ]
    for path in sorted((ROOT / "tasks").glob("*/results/raw-measurements.csv")):
        model = "GPT-OSS-120B" if "gpt_oss" in path.parts[-3] else "Qwen3.6-27B"
        passes = [("qualification", path)]
        profile = path.parent / "solver-profiling/raw-measurements.csv"
        if profile.exists():
            passes.append(("additional profiling during the solver attempt", profile))
        for label, source in passes:
            with source.open(newline="") as stream:
                rows = list(csv.DictReader(stream))
            link = source.relative_to(ROOT).as_posix()
            lines.extend(["", f"## {model} · {label}", "", f"[Per-repetition CSV](../../{link})", "",
                          "| Metric | Unit | Arm | n | Mean | Min | Max | Sample SD |",
                          "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |"])
            for workload, profile, metric, unit, field in GROUPS + [("high_load", "*", "High load combined", "requests/s", "request_throughput")]:
                for side in ("candidate", "pristine"):
                    group = [r for r in rows if r["workload"] == workload and r["side"] == side]
                    if profile == "*":
                        repetitions = defaultdict(list)
                        for r in group:
                            repetitions[r["evidence"].rsplit("_meas", 1)[1]].append(float(r[field]))
                        values = [geometric_mean(v) for v in repetitions.values()]
                    else:
                        values = [float(r[field]) for r in group if r["profile"] == profile]
                    sd = f"{stdev(values):.5f}" if len(values) > 1 else "N/A"
                    lines.append(f"| {metric} | {unit} | {side} | {len(values)} | {mean(values):.5f} | "
                                 f"{min(values):.5f} | {max(values):.5f} | {sd} |")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    print(render(), end="")
