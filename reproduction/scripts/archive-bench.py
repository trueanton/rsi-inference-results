#!/usr/bin/env python3
"""Preserve each version of raw public output before later engine boots reuse its filename."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

for name in ("ALL_PROXY","HTTP_PROXY","HTTPS_PROXY","NO_PROXY"):
    os.environ.pop(name,None)
    os.environ.pop(name.lower(),None)
run = Path(sys.argv[1]).resolve()
job = (run / "job-id").read_text().strip()
agent_dir = Path(sys.argv[2]).resolve() if len(sys.argv)>2 else run / "logs/agent"
if not agent_dir.is_relative_to(run):
    raise ValueError("Agent log directory must belong to this run")
raw = run / "raw-public"
raw.mkdir(exist_ok=True)
index = raw / "index.jsonl"
seen = set()
if index.exists():
    for line in index.read_text().splitlines():
        row = json.loads(line)
        seen.add((row["source"], row["mtime_ns"], row["sha256"]))

def snapshot():
    for path in agent_dir.glob("*bench*/bench_*.json"):
        try:
            with path.open("rb") as stream:
                data = stream.read()
                stamp = os.fstat(stream.fileno()).st_mtime_ns
            doc = json.loads(data)
        except (OSError, ValueError):
            continue
        digest = hashlib.sha256(data).hexdigest()
        source = str(path.relative_to(run))
        key = source, stamp, digest
        if key in seen:
            continue
        target = raw / f"{stamp}_{path.name}"
        target.write_bytes(data)
        row = dict(source=source,mtime_ns=stamp,sha256=digest,file=target.name,
                   completed=doc.get("completed",doc.get("successful_requests")),failed=doc.get("failed"))
        with index.open("a") as stream:
            stream.write(json.dumps(row)+"\n")
        seen.add(key)

next_query = 0.0
while True:
    snapshot()
    if time.monotonic() < next_query:
        time.sleep(6)
        continue
    next_query = time.monotonic() + 90
    q = subprocess.run(["squeue","--me","-h","-o","%i"],capture_output=True,text=True)
    if q.returncode == 0 and job not in q.stdout.split():
        snapshot()
        with (run/"slurm-archive-state.txt").open("w") as out:
            subprocess.run(["scontrol","show","job",job],stdout=out,stderr=subprocess.STDOUT)
        break
    time.sleep(8)
