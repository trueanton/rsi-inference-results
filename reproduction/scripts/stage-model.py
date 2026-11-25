#!/usr/bin/env python3
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

key=sys.argv[1]
exp=Path("@BENCH_ROOT@/experiments")
entry=json.loads((exp/"configs/models.json").read_text())[key]
verified=json.loads((exp/"configs"/f"{key}-verified.json").read_text())
assert entry["revision"]==verified["revision"]
parent=Path("@SHARED_ROOT@/models")/entry["repo"].split("/")[1]
parent.mkdir(parents=True, mode=0o700, exist_ok=True)
dest=parent/entry["revision"]
incoming=parent/(entry["revision"]+".incoming")
if dest.exists():
    if (dest/".rsi-verified.json").read_text()!=json.dumps(verified,sort_keys=True):
        raise ValueError(f"Existing shared copy differs at {dest}")
else:
    incoming.mkdir(mode=0o700, exist_ok=True)
    print("Staging verified files",entry["expected_bytes"],"bytes from",entry["destination"],"to",incoming,flush=True)
    for name,info in entry["files"].items():
        if Path(name).name!=name: raise ValueError(name)
        dst=incoming/name
        if not dst.exists() or dst.stat().st_size!=info["bytes"]:
            shutil.copyfile(Path(entry["destination"])/name,dst)
        with dst.open("rb") as f:
            if hashlib.file_digest(f,"sha256").hexdigest()!=verified["sha256"][name]:
                raise ValueError(f"Staged file failed digest: {dst}")
    (incoming/".rsi-verified.json").write_text(json.dumps(verified,sort_keys=True))
    incoming.rename(dest)
print("Verified shared model",dest,flush=True)
