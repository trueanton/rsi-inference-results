#!/usr/bin/env python3
"""Check the original benchmark summary against every persisted raw run."""
import argparse
import hashlib
from collections import Counter
import json
import math
from pathlib import Path

def audit(run):
    manifest = json.loads((run/"manifest.json").read_text())
    public = Path("@BENCH_ROOT@/ml-rsi-inference-bench/tasks")/manifest["task"]/"environment/public/workloads.json"
    workloads = json.loads(public.read_text())["workloads"]
    agent = run/"logs/agent"
    summary = json.loads((agent/"bench.json").read_text())
    correctness = json.loads((agent/"correctness.json").read_text())
    # The Qwen public helper records paired mode on each workload. GPT also writes a top-level mode.
    qwen = manifest["task"] == "optimize_qwen3_6_27b_1xh100_open"
    if ("mode" in summary or not qwen) and summary.get("mode") != "paired":
        raise ValueError("Public benchmark did not report paired mode")
    rows = summary["per_workload"]
    if set(rows) != {wl["name"] for wl in workloads} or any(row["baseline_source"] != "live_pristine" for row in rows.values()):
        raise ValueError("Every public workload must include its live pristine comparison")
    if correctness["correctness_ok"] is not True:
        raise ValueError("Passing public correctness is required")
    observed = Counter()
    records = []
    for line in (run/"raw-public/index.jsonl").read_text().splitlines():
        index = json.loads(line)
        data = (run/"raw-public"/index["file"]).read_bytes()
        if hashlib.sha256(data).hexdigest() != index["sha256"]:
            raise ValueError("Raw evidence SHA-256 mismatch: "+index["file"])
        raw = json.loads(data)
        source = Path(index["source"]).name
        observed[source] += 1
        records.append((source,raw,index["file"]))
    verified = []
    for wl in workloads:
        name=wl["name"]
        boots=summary["boots"][name]
        repeats=summary["num_runs"][name]
        if not all(summary["per_workload"][name]["workload"].get(k)==wl.get(k) for k in ("input_len","output_len","num_prompts","max_concurrency","profiles")):
            raise ValueError(f"Workload differs for {name}")
        for side in ("candidate","pristine"):
            row=summary["per_workload"][name]
            measurements=row[side+"_runs"]
            if row["baseline_source"]!="live_pristine" or len(measurements)!=boots*repeats or not all(math.isfinite(x) and x>0 for x in measurements):
                raise ValueError(f"Missing or invalid per-workload score for {side} {name}")
            for prof in wl.get("profiles",[None]):
                count=wl["num_prompts"]
                concurrency=prof["concurrency"] if prof else wl["max_concurrency"]
                label=f"{name}_{side}_{prof['name']}" if prof else f"{side}_{name}"
                for i in range(repeats):
                    filename=f"bench_{label}_meas{i}.json"
                    if observed[filename]!=boots:
                        raise ValueError(f"{filename}: expected {boots} boots, found {observed[filename]}")
                    for source,doc,evidence in records:
                        if source!=filename:
                            continue
                        expect=dict(completed=count,failed=0,num_prompts=count,max_concurrency=concurrency,
                                    total_input_tokens=count*wl["input_len"],total_output_tokens=count*wl["output_len"])
                        for k,n in expect.items():
                            if doc.get(k)!=n:
                                raise ValueError(f"{evidence}: {k}={doc.get(k)}, expected {n}")
                        verified.append(dict(side=side,workload=name,profile=prof["name"] if prof else None,
                            evidence=evidence,**{k:doc[k] for k in (*expect,"duration","median_tpot_ms","median_ttft_ms","output_throughput","request_throughput","total_token_throughput")}))
    return dict(valid=True,bench_geomean=summary["speedup_geomean"],correctness=correctness["overall_pass_rate"],raw_measurements=verified)

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("run",type=Path)
    args=parser.parse_args()
    report=audit(args.run)
    (args.run/"public-audit.json").write_text(json.dumps(report,indent=2)+"\n")
    print("Validated",len(report["raw_measurements"]),"raw measurements")
