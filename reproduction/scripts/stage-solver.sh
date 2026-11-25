#!/usr/bin/env bash
set -euo pipefail
umask 077
unset ALL_PROXY all_proxy HTTP_PROXY http_proxy HTTPS_PROXY https_proxy NO_PROXY no_proxy
exp=@BENCH_ROOT@/experiments
tools=@LOCAL_ROOT@/tools
shared=@SHARED_ROOT@/tools
dest="$tools/mini-swe-agent-2.4.6"
uv="$tools/download-tools/bin/uv"
export UV_CACHE_DIR=@LOCAL_ROOT@/cache/uv
"$uv" venv --allow-existing --python /usr/bin/python3.12 "$dest"
"$uv" pip install --python "$dest/bin/python" -r "$exp/configs/solver-requirements.txt"
"$uv" pip check --python "$dest/bin/python"
"$uv" pip freeze --python "$dest/bin/python" > "$exp/configs/solver-requirements.txt"
"$dest/bin/python" -c 'import importlib.metadata as m; print(m.version("mini-swe-agent"))'
archive="$shared/mini-swe-agent-2.4.6.tar.gz"
tar -czf "$archive.new" -C "$tools" mini-swe-agent-2.4.6
sha256sum "$archive.new" | cut -d' ' -f1 > "$exp/configs/solver-archive.sha256"
mv -T "$archive.new" "$archive"
