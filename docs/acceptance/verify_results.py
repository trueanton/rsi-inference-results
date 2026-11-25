"""Recompute paired A/A scores and verify workload coverage using only the standard library."""
import csv
import json
import math
import re
from collections import defaultdict
from pathlib import Path
from statistics import geometric_mean, mean

ROOT = Path(__file__).resolve().parents[2]
WORKLOADS = {
    "decode_heavy": (1024, 8192, 4),
    "prefill_heavy": (8192, 1, 256),
    "high_load": (1024, 1024, 256),
}
SIDES = ("candidate", "pristine")


def require(condition, description):
    if not condition:
        raise ValueError(description)


def trimmed_mean(values):
    return mean(sorted(values)[1:-1] if len(values) >= 3 else values)


def scores_for_side(task, rows, pins):
    scores = defaultdict(list)
    high_load = defaultdict(dict)
    repeats = pins["measured_repetitions"]
    expected_high = repeats["high_load_per_concurrency"]
    for row in rows:
        workload = row["workload"]
        n_input, n_output, n_prompts = WORKLOADS[workload]
        concurrency = int(row["max_concurrency"])
        expected = {
            "num_prompts": n_prompts, "completed": n_prompts, "failed": 0,
            "total_input_tokens": n_input * n_prompts,
            "total_output_tokens": n_output * n_prompts,
        }
        require(all(int(row[k]) == v for k, v in expected.items()), f"{task}: incomplete {row['evidence']}")
        if workload == "high_load":
            require(concurrency in (16, 32, 64) and row["profile"] == f"c{concurrency}", "Invalid high-load profile")
            match = re.search(r"_meas(\d+)\.json$", row["evidence"])
            require(match is not None, "Missing repetition identifier")
            batch = high_load[int(match.group(1))]
            require(concurrency not in batch, "Duplicate high-load measurement")
            batch[concurrency] = float(row["request_throughput"])
        else:
            require(concurrency == 1 and not row["profile"], f"Unexpected profile for {workload}")
            metric = "median_tpot_ms" if workload == "decode_heavy" else "median_ttft_ms"
            scores[workload].append(1000 / float(row[metric]))
    require(set(high_load) == set(range(expected_high)), "Missing high-load repetitions")
    for profiles in high_load.values():
        require(set(profiles) == {16, 32, 64}, "Incomplete high-load repetition")
        scores["high_load"].append(geometric_mean(profiles.values()))
    expected_counts = {
        "decode_heavy": pins["decode_boots"] * repeats["decode_heavy"],
        "prefill_heavy": repeats["prefill_heavy"], "high_load": expected_high,
    }
    require(all(len(scores[k]) == v for k, v in expected_counts.items()), f"{task}: wrong repetition count")
    return {name: trimmed_mean(values) for name, values in scores.items()}


def verify_task(folder):
    data = folder / "results"
    recorded = json.loads((data / "summary.json").read_text())
    pins = json.loads((folder / "environment/pins/runtime.json").read_text())
    with (data / recorded["raw"]).open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    require(len(rows) == recorded["measured_runs"], "Unexpected measurement count")
    require(len({row["evidence"] for row in rows}) == len(rows), "Duplicate archived measurement")
    require({row["side"] for row in rows} == set(SIDES), "Missing or unknown comparison arm")
    arms = {side: scores_for_side(folder.name, [r for r in rows if r["side"] == side], pins) for side in SIDES}
    ratio = geometric_mean(arms["candidate"][k] / arms["pristine"][k] for k in WORKLOADS)
    require(math.isclose(ratio, recorded["paired_unchanged_ratio"], rel_tol=0, abs_tol=5e-8), "Paired ratio mismatch")
    total = sum(int(r["completed"]) for r in rows)
    require(total == recorded["completed_requests"] and recorded["failed_requests"] == 0, "Request total mismatch")
    if recorded["solver_attempts"]:
        solver = json.loads((data / "solver-result.json").read_text())
        verifier = json.loads((data / "verifier-metrics.json").read_text())
        final = solver["final_verifier"]
        proof = final["tree_proof"]
        require(proof["working_tree_clean"] and proof["archived_tree"] == proof["fresh_tree"] == pins["measured_engine_tree"], "Tree mismatch")
        require(proof["solver_commit"] == proof["solver_base_commit"] and proof["fresh_commit"] == proof["fresh_base_commit"], "Unexpected source change")
        require(verifier["reason"] == final["reason"] == "no_patch" and final["rewards"]["reward"] == 0, "Verifier mismatch")
        patch = (folder / "solution/candidate.patch").read_bytes()
        require(len(patch) == solver["committed_patch_bytes"] == solver["uncommitted_patch_bytes"] == 0, "Unexpected solver patch")
    print(f"{pins['model']}: {len(rows)} measurements, {total:,} requests, {ratio:.6f}×")
    return len(rows), total


def main():
    summaries = sorted((ROOT / "tasks").glob("*/results/summary.json"))
    require(len(summaries) == 2, "Expected both campaign tasks")
    results = [verify_task(p.parents[1]) for p in summaries]
    print(f"Verified {sum(n for n, _ in results)} measurements and {sum(t for _, t in results):,} requests.")


if __name__ == "__main__":
    main()
