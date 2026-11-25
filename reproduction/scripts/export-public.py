#!/usr/bin/env python3
"""Export the unchanged-engine measurements without folding profiles into independent tasks."""
import csv
import json
from pathlib import Path
from statistics import mean, stdev
import sys

def describe(samples):
    return {"n": len(samples), "mean":mean(samples), "sample_sd":stdev(samples) if len(samples)>1 else None,
            "minimum": min(samples), "maximum": max(samples), "raw":samples}

run=Path(sys.argv[1]).resolve()
audit=json.loads((run/"public-audit.json").read_text())
assert audit["valid"]
bench=json.loads((run/"logs/agent/bench.json").read_text())
manifest=json.loads((run/"manifest.json").read_text())
rows=audit["raw_measurements"]
with (run/"raw-measurements.csv").open("w") as stream:
    out=csv.DictWriter(stream,fieldnames=list(rows[0]))
    out.writeheader()
    out.writerows(rows)
units={"decode_heavy":"1000 / median TPOT (ms), tokens/s",
       "prefill_heavy":"1000 / median TTFT (ms), reciprocal seconds",
       "high_load":"geometric mean of request throughput at c16, c32 and c64, requests/s"}
result={"run":run.name,"task":manifest["task"],"classification":manifest["classification"],
        "overall_paired_speedup":bench["speedup_geomean"],"workload":{},"high_load_profiles":{},
        "raw_measurements":"raw-measurements.csv","candidate_provenance":bench["candidate_provenance"]}
for name,values in bench["per_workload"].items():
    result["workload"][name]=dict(unit=units[name],speedup=values["speedup"],
        candidate=values["candidate_stats"],pristine=values["pristine_stats"],
        candidate_runs=values["candidate_runs"],pristine_runs=values["pristine_runs"])
for profile in sorted({r["profile"] for r in rows if r["profile"]}):
    z={side:describe([r["request_throughput"] for r in rows if r["profile"]==profile and r["side"]==side])
       for side in ("candidate","pristine")}
    z["unit"]="requests/s"
    z["ratio_of_profile_means"]=z["candidate"]["mean"]/z["pristine"]["mean"]
    result["high_load_profiles"][profile]=z
(run/"public-results.json").write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps({name:values["speedup"] for name,values in bench["per_workload"].items()}))
