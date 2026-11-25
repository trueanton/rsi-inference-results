#!/usr/bin/env python3
"""Compare the active distribution metadata against the original executable task lock."""
import hashlib
from importlib import metadata
import json
from pathlib import Path
import sys
from packaging.requirements import Requirement
installed_lock=Path("/opt/infb/requirements.lock")
expected_lock=Path(sys.argv[1])
if installed_lock.read_bytes()!=expected_lock.read_bytes():
    raise ValueError("Image lock differs from the upstream task Dockerfile")
checks={}
errors=[]
for line in expected_lock.read_text().splitlines():
    line=line.strip()
    if not line or line.startswith(("#","--")):
        continue
    req=Requirement(line)
    if req.marker and not req.marker.evaluate():
        continue
    try:
        version=metadata.version(req.name)
    except metadata.PackageNotFoundError:
        version=None
    checks[req.name]=dict(expected=str(req.specifier),installed=version)
    if version is None or not req.specifier.contains(version,prereleases=True):
        errors.append((req.name,str(req.specifier),version))
print(json.dumps(dict(lock_sha256=hashlib.sha256(expected_lock.read_bytes()).hexdigest(),packages=checks,errors=errors),indent=2))
if errors:
    raise SystemExit("Installed distributions do not satisfy the original task lock")
