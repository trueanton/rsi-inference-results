#!/usr/bin/env python3
"""Compare the solver's archived public profiling requests with the qualified workload contract."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys

run=Path(sys.argv[1]).resolve()
base=Path((run/"qualified-baseline.path").read_text().strip())
reference=json.loads((base/"public-audit.json").read_text())
conditions=("completed","failed","num_prompts","max_concurrency","total_input_tokens","total_output_tokens")
def name(archived):
    return re.sub(r"^\d+_","",Path(archived).name)
def key(filename,record):
    return (name(filename),*(record[k] for k in conditions))
expected=Counter(key(x["evidence"],x) for x in reference["raw_measurements"])
observed=Counter()
counts={}
names=[]
for line in (run/"raw-public/index.jsonl").read_text().splitlines():
    item=json.loads(line)
    filename=Path(item["source"]).name
    if "_meas" not in filename:
        continue
    raw=(run/"raw-public"/item["file"]).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=item["sha256"]:
        raise ValueError("Digest changed for "+item["file"])
    record=json.loads(raw)
    observed[key(filename,record)]+=1
    side="pristine" if "pristine" in filename else "candidate"
    if side not in counts:
        counts[side]=dict(measurements=0,completed=0,failed=0)
    counts[side]["measurements"]+=1
    for k in ("completed","failed"):
        counts[side][k]+=record[k]
    names.append(item["file"])
if observed!=expected:
    raise ValueError("Archived requests or repetitions differ from qualification")
traj=json.loads((run/"host-solver/mini-swe-agent.trajectory.json").read_text())
prefix="=== run_benchmark summary (paired mode) ==="
reports=[]
for message in traj["messages"]:
    if message["role"]=="tool":
        log=message.get("extra",{}).get("raw_output","")
        if isinstance(log,str) and prefix in log:
            reports.append(log[log.rindex(prefix):].strip())
if len(reports)!=1:
    raise ValueError("Expected exactly one complete profiling summary")
result=dict(source="solver profiling of the unchanged public engine",by_side=counts,
            reference_run=base.name,verified_raw_files=names,public_harness_summary=reports[0])
(run/"solver-profile.json").write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps(counts))
