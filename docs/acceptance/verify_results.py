"""Recompute paired A/A scores and verify workload coverage using only the standard library."""
import csv
import gzip
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


def verify_correctness(data, recorded):
    correctness = json.loads((data / "correctness.json").read_text())
    per_prompt = correctness["per_prompt"]
    require(correctness["correctness_ok"] is recorded["correctness_passed"] is True and
            len(per_prompt) == correctness["num_prompts"] == recorded["prompts"] and
            sum(p["n_passing"] for p in per_prompt) == correctness["num_positions_passing"] == recorded["correct_positions"] and
            sum(p["n_positions"] for p in per_prompt) == correctness["num_positions_total"] == recorded["total_positions"],
            "Correctness evidence mismatch")


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
    verify_correctness(data, recorded)
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


# Each metric is rounded only after aggregation for the published tables.
PROFILE_METRICS = (
    ("requests_per_s", "request_throughput", 4),
    ("total_tokens_per_s", "total_token_throughput", 2),
    ("output_tokens_per_s", "output_throughput", 2),
    ("median_ttft_ms", "median_ttft_ms", 2),
    ("median_tpot_ms", "median_tpot_ms", 2),
)


def verify_profile_tables(task_dir, model, profiles):
    with (task_dir / "results/raw-measurements.csv").open(newline="") as stream:
        a100 = defaultdict(list)
        for row in csv.DictReader(stream):
            if row["side"] == "pristine":
                a100[row["workload"], row["max_concurrency"]].append(row)
    reports = {gpu: (ROOT / f"docs/{gpu}.md").read_text().splitlines() for gpu in ("a100", "h100")}
    comparison = (ROOT / "docs/qualification-comparison.md").read_text()
    heading = f"### {model} ·"
    require(comparison.count(heading) == 1, f"Missing or duplicate archived comparison section for {model}")
    section = comparison.split(heading)[1].split("\n#")[0].splitlines()
    for h100 in profiles:
        workload, c = h100["workload"], h100["concurrency"]
        samples = a100[workload, c]
        require(len(samples) == int(h100["measured_repetitions"]), f"{model}/{workload}: repetition mismatch")
        # Prefill returns only one token and has no TPOT.
        cells = {"a100": {}, "h100": {}}
        for field, source, decimals in PROFILE_METRICS:
            if workload == "prefill_heavy" and field == "median_tpot_ms":
                cells["a100"][field] = cells["h100"][field] = "—"
                continue
            a = trimmed_mean([float(r[source]) for r in samples])
            cells["a100"][field] = f"{a:,.{decimals}f}"
            cells["h100"][field] = f"{float(h100[field]):,.{decimals}f}"
        for gpu, values in cells.items():
            row = [model, workload.replace("_", " "), c, *values.values()]
            require("| " + " | ".join(row) + " |" in reports[gpu], f"{gpu}/{model}/{workload}/c{c}: stale profile table")
        label, metric, field = {
            "decode_heavy": ("Decode", "Time per output token (ms/token) ↓", "median_tpot_ms"),
            "prefill_heavy": ("Prefill", "Time to first token (ms) ↓", "median_ttft_ms"),
            "high_load": ("High load", "Requests/s ↑", "requests_per_s"),
        }[workload]
        row = [f"{label}, c{c}", metric, cells["a100"][field], cells["h100"][field]]
        require("| " + " | ".join(row) + " |" in section, f"{model}/{workload}/c{c}: stale archived comparison")


def h100_repetitions(bench):
    reps = bench["num_runs"]
    return {"decode_boots": bench["boots"]["decode_heavy"], "measured_repetitions": {
        "decode_heavy": reps["decode_heavy"], "prefill_heavy": reps["prefill_heavy"],
        "high_load_per_concurrency": reps["high_load"]}}


def verify_h100_evidence(folder, summary, pristine):
    rows = read_measurements(folder)
    groups = defaultdict(list)
    for r in rows:
        groups[r["side"], r["workload"], int(r["max_concurrency"])].append(r)
    expected = {(side, r["workload"], int(r["concurrency"])) for side in SIDES for r in pristine}
    require(set(groups) == expected and len(rows) == summary["measured_runs"], "H100 timed profile coverage mismatch")
    require(sum(int(r["completed"]) for r in rows) == summary["completed_requests"], "H100 raw request total differs")
    with (folder / "paired-profiles.csv").open(newline="") as stream:
        paired = list(csv.DictReader(stream))
    require(len(paired) == len(expected) and {(p["arm"], p["workload"], int(p["concurrency"])) for p in paired} == expected,
            "Invalid H100 paired profile export")
    pristine_by_profile = {(r["workload"], int(r["concurrency"])): r for r in pristine}
    fields = {"request_throughput": "requests_per_s", "output_throughput": "output_tokens_per_s",
              "total_token_throughput": "total_tokens_per_s", "median_ttft_ms": "median_ttft_ms",
              "median_tpot_ms": "median_tpot_ms", "p99_ttft_ms": None, "p99_tpot_ms": None}
    for profile in paired:
        arm, workload, concurrency = profile["arm"], profile["workload"], int(profile["concurrency"])
        group = groups[arm, workload, concurrency]
        require(len(group) == int(profile["repetitions"]) and all(r["num_prompts"] == profile["requests_per_repetition"]
                for r in group), "H100 profile request or repetition count mismatch")
        for key, public_key in fields.items():
            if workload == "prefill_heavy" and "tpot" in key:
                require(profile[key] == "", "Expected empty TPOT for one generated token")
                continue
            value = trimmed_mean([float(r[key]) for r in group])
            require(math.isclose(value, float(profile[key]), rel_tol=1e-12), f"H100 raw {key} differs for {profile}")
            if arm == "pristine" and public_key:
                require(math.isclose(value, float(pristine_by_profile[workload, concurrency][public_key]), rel_tol=1e-12),
                        f"H100 pristine {key} differs")
    bench = json.loads((folder / "bench.json").read_text())
    pins = h100_repetitions(bench)
    arms = {}
    for side in SIDES:
        arms[side] = scores_for_side(summary["task"], [r for r in rows if r["side"] == side], pins)
        for name, score in arms[side].items():
            ref = bench["per_workload"][name][side + "_stats"]["trimmed_mean"]
            require(math.isclose(score, ref, rel_tol=1e-12), f"H100 {side}/{name} differs from bench.json")
        observed_boots = [float(r["output_throughput"]) for r in sorted(groups[side, "decode_heavy", 1],
                                                                        key=lambda r: r["evidence"])]
        require(observed_boots == summary["decode_boot_output_tokens_per_s"][side], f"H100 {side} decode boots differ")
    ratios = [arms["candidate"][w] / arms["pristine"][w] for w in WORKLOADS]
    for name, ratio in zip(WORKLOADS, ratios):
        require(math.isclose(ratio, summary["workload_ratios"][name], rel_tol=1e-12), f"H100 {name} ratio differs")
    require(math.isclose(geometric_mean(ratios), bench["speedup_geomean"], rel_tol=1e-12), "H100 raw paired score differs")
    verify_correctness(folder, summary)
    native = json.loads((folder / "verifier-metrics.json").read_text())
    reward = json.loads((folder / "reward.json").read_text())
    require(native["classification_kind"] == "empty" and native["reason"] == "no_patch" and reward["reward"] == 0 and
            summary["native_verifier"] == {"classification_kind": native["classification_kind"],
                                           "reason": native["reason"], "reward": reward["reward"]}, "H100 edit gate mismatch")
    peaks = {}
    with gzip.open(folder / "gpu-samples-5s.csv.gz", "rt", newline="") as stream:
        for sample in csv.DictReader(stream):
            device = sample["device"]
            peaks[device] = max(peaks.get(device, 0), int(sample["memory_used_mib"]))
    require(peaks == summary["sampled_peak_memory_mib_by_device"] and len(peaks) == summary["hardware"]["gpu_count"],
            "H100 telemetry peak mismatch")


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
    require(summary["solver_attempts"] == int(outcome["solver_attempts"]) == 0 and summary["agent_speedup"] is None,
            f"{task}: inconsistent H100 baseline outcome")
    task_dir = ROOT / "tasks" / task
    display_model = {"openai/gpt-oss-120b": "GPT-OSS-120B", "Qwen/Qwen3.6-27B": "Qwen3.6-27B"}[model["id"]]
    require(all(r["model"] == display_model for r in rows), f"{task}: profile model mismatch")
    a100 = json.loads((task_dir / "environment/pins/runtime.json").read_text())
    for h_key, a_key in (("benchmark_revision", "benchmark_revision"), ("engine_revision", "vllm_revision"),
                         ("measured_engine_tree", "measured_engine_tree")):
        require(summary["runtime"][h_key] == a100[a_key], f"{task}: cross-campaign {h_key} differs")
    verify_profile_tables(task_dir, display_model, rows)
    verify_h100_evidence(folder, summary, rows)
    print(f"H100 job {job['job_id']}: {2 * measured} raw timings, {2 * requests:,} verified requests across both arms")


def verify_optimization(folder, display, pins):
    """Check the H100 patch, controller ledger, correctness and published ratio cells."""
    name = folder.name
    solver = json.loads((folder / "solver.json").read_bytes())
    sealed = json.loads((folder / "sealed.json").read_bytes())
    patch = (folder / "candidate.patch").read_bytes()
    require(patch and hashlib.sha256(patch).hexdigest() == sealed["patch_sha256"] == solver["final_patch_sha256"],
            f"{name}: frozen patch checksum mismatch")
    require(sealed["base_tree"] != sealed["candidate_tree"], f"{name}: candidate equals baseline")
    with (folder / "trajectory.csv").open(newline="") as stream:
        ledger = list(csv.DictReader(stream))
    require([int(row["step"]) for row in ledger] == list(range(1, solver["model_replies"] + 1)),
            f"{name}: missing or repeated reply")
    for key in ("prompt_tokens", "completion_tokens"):
        require(sum(int(row[key]) for row in ledger) == solver[key], f"{name}: {key} mismatch")
    require(all(int(row["prompt_tokens"]) + solver["completion_reserve"] <= solver["context_tokens"]
                and int(row["completion_tokens"]) <= solver["completion_reserve"] for row in ledger),
            f"{name}: context or generation limit exceeded")

    readme = (ROOT / "README.md").read_text().splitlines()
    row, = [line for line in readme if line.startswith(f"| [{display} ·")]
    for gate in ("official", "public"):
        path = folder / f"{gate}-correctness.json"
        if gate == "public" and name == "gpt" and not path.exists():
            continue
        correctness = json.loads(path.read_bytes())
        prompts = correctness["per_prompt"]
        if gate == "official":
            total = sum(p["n_positions_compared"] for p in prompts)
            passed = sum(round(p["logprob_pass_rate"] * p["n_positions_compared"]) for p in prompts)
            require(f"{passed:,}/{total:,}" in row, f"{name}: stale README correctness")
        else:
            total = sum(p["n_positions"] for p in prompts)
            passed = sum(p["n_passing"] for p in prompts)
        require((len(prompts), passed, total) == (correctness["num_prompts"],
                correctness["num_positions_passing"], correctness["num_positions_total"]), f"{name}: position mismatch")
        require(correctness["correctness_ok"] and math.isclose(passed / total, correctness["overall_pass_rate"]),
                f"{name}: correctness evidence mismatch")

    if name == "qwen":
        require((folder / "official-timings.zip").exists() and (folder / "repeat-1-timings.zip").exists(),
                "Missing Qwen verification evidence")
    for archive in sorted(folder.glob("*-timings.zip")):
        stage = archive.name.removesuffix("-timings.zip")
        scores = json.loads((folder / f"{stage}.json").read_bytes())
        arms = defaultdict(list)
        with ZipFile(archive) as source:
            require(len(source.namelist()) == len(set(source.namelist())), f"{archive}: duplicate timing")
            for member in source.namelist():
                d = json.loads(source.read(member))
                c = d["max_concurrency"]
                side = "pristine" if "pristine" in member else "candidate"
                workload = "high_load" if c > 1 else "prefill_heavy" if "prefill" in member else "decode_heavy"
                arms[side].append(dict(d, workload=workload, evidence=member, profile=f"c{c}" if c > 1 else ""))
        values = {side: scores_for_side(name, arms[side], pins) for side in SIDES}
        ratios = [values["candidate"][k] / values["pristine"][k] for k in WORKLOADS]
        overall = geometric_mean(ratios)
        native = stage == "official"
        published = scores["speedup_per_workload" if native else "speedup"]
        require(all(math.isclose(r, published[k], rel_tol=1e-12) for k, r in zip(WORKLOADS, ratios))
                and math.isclose(overall, scores["speedup_geomean" if native else "geomean"], rel_tol=1e-12),
                f"{name}: {stage} differs from raw records")
        if native or stage == "repeat-1":
            require(f"{overall:.5f}×" in row, f"{name}: stale README {stage} score")
        requests = sum(r["completed"] for group in arms.values() for r in group)
        print(f"{display} H100 optimization {stage}: {overall:.6f}×, {requests:,} timed requests")


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
    print("Checked the pristine-arm comparison tables against both hardware exports.")
    for outcome in h100:
        task = ROOT / "tasks" / outcome["task"]
        key, display = ("gpt", "GPT-OSS-120B") if "gpt_oss" in task.name else ("qwen", "Qwen3.6-27B")
        baseline = task / "results/h100" / outcome["run_id"]
        pins = h100_repetitions(json.loads((baseline / "bench.json").read_bytes()))
        folder = ROOT / "docs/evidence/h100" / key
        tree = json.loads((baseline / "summary.json").read_bytes())["runtime"]["measured_engine_tree"]
        require(tree == json.loads((folder / "sealed.json").read_bytes())["base_tree"], "Wrong optimization base")
        verify_optimization(folder, display, pins)


if __name__ == "__main__":
    main()
