"""Recompute paired A/A scores and verify workload coverage using only the standard library."""
import csv
import hashlib
import json
import math
import re
from collections import defaultdict
from pathlib import Path
from statistics import geometric_mean, mean
from zipfile import ZipFile

from variation import render

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


def read_measurements(data, filename="raw-measurements.csv"):
    with (data / filename).open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    with ZipFile(data / "timed-json.zip") as archive:
        require(sorted(archive.namelist()) == sorted(r["evidence"] for r in rows), "Raw file list mismatch")
        for row in rows:
            record = json.loads(archive.read(row["evidence"]))
            for key in row.keys() - {"side", "workload", "profile", "evidence"}:
                require(str(record[key]) == row[key], f"{row['evidence']}: raw JSON differs for {key}")
    return rows


def verify_task(folder):
    data = folder / "results"
    recorded = json.loads((data / "summary.json").read_text())
    pins = json.loads((folder / "environment/pins/runtime.json").read_text())
    key = "gpt" if "gpt_oss" in folder.name else "qwen"
    lock = (ROOT / "reproduction/configs" / f"{key}-upstream-runtime.lock").read_bytes()
    audit = json.loads((folder / "environment/pins/runtime-lock-audit.json").read_text())
    require(not audit["errors"] and audit["lock_sha256"] == hashlib.sha256(lock).hexdigest(), "Runtime lock mismatch")
    require(f"random-prompt seed: {pins['benchmark_seed']} " in (data / "benchmark-settings.txt").read_text(),
            "Benchmark seed mismatch")
    rows = read_measurements(data, recorded["raw"])
    correctness = json.loads((data / "correctness.json").read_text())
    per_prompt = correctness["per_prompt"]
    require(correctness["correctness_ok"] is recorded["correctness_passed"] is True and
            len(per_prompt) == correctness["num_prompts"] == recorded["prompts"] and
            sum(p["n_passing"] for p in per_prompt) == correctness["num_positions_passing"] == recorded["correct_positions"] and
            sum(p["n_positions"] for p in per_prompt) == correctness["num_positions_total"] == recorded["total_positions"],
            "Correctness evidence mismatch")
    require(recorded["agent_speedup"] is None and recorded["native_h100_score"] is None, "Unexpected score")
    require(len(rows) == recorded["measured_runs"], "Unexpected measurement count")
    require(len({row["evidence"] for row in rows}) == len(rows), "Duplicate archived measurement")
    require({row["side"] for row in rows} == set(SIDES), "Missing or unknown comparison arm")
    arms = {side: scores_for_side(folder.name, [r for r in rows if r["side"] == side], pins) for side in SIDES}
    ratio = geometric_mean(arms["candidate"][k] / arms["pristine"][k] for k in WORKLOADS)
    require(math.isclose(ratio, recorded["paired_unchanged_ratio"], rel_tol=0, abs_tol=5e-8), "Paired ratio mismatch")
    bench = json.loads((data / "bench.json").read_text())
    require(bench["candidate_provenance"]["tree_sha"] == pins["measured_engine_tree"]
            and bench["candidate_provenance"]["worktree_clean"], "Wrong qualification tree")
    require(bench["num_warmup"] == pins["warmups"] and bench["boots"]["decode_heavy"] == pins["decode_boots"],
            "Benchmark settings mismatch")
    for k in WORKLOADS:
        original = bench["per_workload"][k]
        require(original["baseline_source"] == "live_pristine", "Missing live baseline")
        for side in SIDES:
            require(math.isclose(arms[side][k], original[side + "_stats"]["trimmed_mean"], rel_tol=1e-12),
                    f"{side}/{k}: score differs from benchmark output")
    require(math.isclose(ratio, bench["speedup_geomean"], rel_tol=1e-12), "Archived ratio mismatch")
    total = sum(int(r["completed"]) for r in rows)
    require(total == recorded["completed_requests"] and recorded["failed_requests"] == 0, "Request total mismatch")
    if recorded["solver_attempts"]:
        solver = json.loads((data / "solver-result.json").read_text())
        verifier = json.loads((data / "verifier-metrics.json").read_text())
        extra = read_measurements(data / "solver-profiling")
        for side in SIDES:
            group = [r for r in extra if r["side"] == side]
            scores_for_side(folder.name, group, pins)
            counts = solver["additional_unchanged_profiling"][side]
            require(counts == {"measurements": len(group), "completed": sum(int(r["completed"]) for r in group),
                               "failed": sum(int(r["failed"]) for r in group)}, "Solver profile count mismatch")
        require(len(extra) == sum(s["measurements"] for s in solver["additional_unchanged_profiling"].values()),
                "Unknown profiling arm")
        print(f"GPT solver profiling (separate): {len(extra)} measurements, "
              f"{sum(int(r['completed']) for r in extra):,} requests")
        final = solver["final_verifier"]
        proof = final["tree_proof"]
        require(proof == json.loads((data / "replayed-tree.json").read_text()), "Fresh replay record mismatch")
        require(final["rewards"] == json.loads((data / "final-reward.json").read_text()), "Final reward mismatch")
        state = (folder / "solution/candidate-state.txt").read_text().splitlines()
        require(state == [proof["solver_commit"], proof["solver_base_commit"], proof["archived_tree"], proof["archived_tree"]], "Archived tree record mismatch")
        require(proof["working_tree_clean"] and proof["archived_tree"] == proof["fresh_tree"] == pins["measured_engine_tree"], "Tree mismatch")
        require(proof["solver_commit"] == proof["solver_base_commit"] and proof["fresh_commit"] == proof["fresh_base_commit"], "Unexpected source change")
        require(verifier["reason"] == final["reason"] == "no_patch" and final["rewards"]["reward"] == 0, "Verifier mismatch")
        require(verifier["classification_kind"] == final["classification"] == "empty" and
                recorded["local_optimization_reward"] == final["rewards"]["reward"], "Edit gate mismatch")
        patch = (folder / "solution/candidate.patch").read_bytes()
        require(len(patch) == solver["committed_patch_bytes"] == solver["uncommitted_patch_bytes"] == 0, "Unexpected solver patch")
    print(f"{pins['model']}: {len(rows)} measurements, {total:,} requests, {ratio:.6f}×")
    return len(rows), total


def verify_h100(outcome):
    task = outcome["task"]
    folder = ROOT / "tasks" / task / "results/h100" / outcome["run_id"]
    summary = json.loads((folder / "summary.json").read_text())
    path = folder / summary["pristine_profiles"]
    require(path == ROOT / outcome["throughput"] and summary["task"] == task
            and summary["run_id"] == folder.name, f"{task}: H100 evidence path mismatch")
    with path.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    profiles = {("decode_heavy", 1), ("prefill_heavy", 1), ("high_load", 16), ("high_load", 32), ("high_load", 64)}
    require(len(rows) == len(profiles) and {(r["workload"], int(r["concurrency"])) for r in rows} == profiles,
            f"{task}: incomplete or duplicate H100 profile")
    job = summary["slurm"]
    model = summary["model"]
    gpu_count = 2 if "gpt_oss" in task else 1
    require(job["state"] == "COMPLETED" and job["exit_code"] == "0:0" and str(job["job_id"]) == outcome["slurm_job_id"]
            and outcome["status"] == summary["configuration"] == "qualified_unchanged_baseline",
            f"{task}: H100 qualification status mismatch")
    require(model["revision"] == outcome["checkpoint_revision"] and
            model["tensor_parallelism"] == summary["hardware"]["gpu_count"] == int(outcome["tensor_parallelism"]) == gpu_count,
            f"{task}: H100 configuration mismatch")
    measured = requests = 0
    repeated_profiles = 2 if "gpt_oss" in task else 1
    for row in rows:
        workload = row["workload"]
        label = f"{task}/{workload}/c{row['concurrency']}"
        inputs, outputs, prompts = WORKLOADS[workload]
        reps = int(row["measured_repetitions"])
        require(row["arm"] == "pristine" and row["job_id"] == outcome["slurm_job_id"] and
                row["sacct_node"] == job["node"] and row["sacct_exit"] == job["exit_code"] and
                int(row["h100_count"]) == gpu_count, f"{label}: profile provenance mismatch")
        expected_repetitions = 5 if workload == "prefill_heavy" else repeated_profiles
        require(int(row["requests_per_repetition"]) == prompts and reps == expected_repetitions,
                f"{label}: workload count mismatch")
        rate = float(row["requests_per_s"])
        require(math.isfinite(rate) and rate > 0 and math.isclose(float(row["total_tokens_per_s"]), rate * (inputs + outputs))
                and math.isclose(float(row["output_tokens_per_s"]), rate * outputs), f"{label}: token rate mismatch")
        latency_fields = ["median_ttft_ms"]
        if outputs > 1:
            latency_fields.append("median_tpot_ms")
        else:
            require(row["median_tpot_ms"] == "", f"{label}: unexpected single-token TPOT")
        require(all(0 < float(row[k]) < math.inf for k in latency_fields), f"{label}: invalid latency")
        measured += reps
        requests += prompts * reps
    require(summary["measured_runs"] == 2 * measured and summary["completed_requests_per_arm"] == requests and
            summary["completed_requests"] == 2 * requests and summary["failed_requests"] == 0,
            f"{task}: H100 request or measurement totals differ")
    require(summary["correctness_passed"] and 0 < summary["correct_positions"] <= summary["total_positions"] and
            f"{summary['correct_positions']}/{summary['total_positions']}" == outcome["correctness"],
            f"{task}: H100 correctness totals differ")
    ratios = summary["workload_ratios"]
    require(set(ratios) == set(WORKLOADS) and math.isclose(geometric_mean(ratios.values()), summary["paired_unchanged_ratio"])
            and math.isclose(float(outcome["paired_speedup"]), summary["paired_unchanged_ratio"], rel_tol=0, abs_tol=5e-8),
            f"{task}: reported H100 A/A ratios differ")
    require(summary["solver_attempts"] == int(outcome["solver_attempts"]) == 0 and summary["agent_speedup"] is None and
            summary["native_verifier"] == {"classification_kind": "empty", "reason": "no_patch"},
            f"{task}: inconsistent H100 baseline outcome")
    print(f"H100 job {job['job_id']}: {len(rows)} pristine profiles, {2 * requests:,} reported requests across both arms")


def main():
    summaries = sorted((ROOT / "tasks").glob("*/results/summary.json"))
    require(len(summaries) == 2, "Expected both campaign tasks")
    results = [verify_task(p.parents[1]) for p in summaries]
    require(Path(__file__).with_name("variability.md").read_text() == render(), "Stale variability table")
    print(f"Verified {sum(n for n, _ in results)} A100 qualification measurements and {sum(t for _, t in results):,} requests.")
    with Path(__file__).with_name("outcomes.csv").open(newline="") as stream:
        h100 = [row for row in csv.DictReader(stream) if row["configuration"] == "assigned_h100_baseline"]
    require(len(h100) == len(summaries) and {r["task"] for r in h100} == {p.parents[1].name for p in summaries},
            "Expected one assigned H100 baseline per task")
    for outcome in h100:
        verify_h100(outcome)


if __name__ == "__main__":
    main()
