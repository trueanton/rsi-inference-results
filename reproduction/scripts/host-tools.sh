#!/usr/bin/env bash
set -euo pipefail
unset ALL_PROXY all_proxy HTTP_PROXY http_proxy HTTPS_PROXY https_proxy NO_PROXY no_proxy
umask 077
set -x
root=@BENCH_ROOT@
scratch=@LOCAL_ROOT@
host_tools="$scratch/tools/download-tools"
export PIP_CACHE_DIR="$scratch/cache/pip" UV_CACHE_DIR="$scratch/cache/uv" UV_PROJECT_ENVIRONMENT="$scratch/tools/pier"
if [[ ! -x "$host_tools/bin/python" ]]; then python3 -m venv "$host_tools"; fi
"$host_tools/bin/python" -m pip install -r "$root/experiments/configs/download-tools-requirements.txt"
"$host_tools/bin/python" -m pip check
"$host_tools/bin/python" -m pip freeze > "$root/experiments/configs/download-tools-requirements.txt"
"$host_tools/bin/hf" download --help > "$root/experiments/configs/hf-download-help.txt"
cd "$root/ml-rsi-inference-bench"
"$host_tools/bin/uv" sync --frozen --python /usr/bin/python3
"$host_tools/bin/uv" pip freeze --python "$UV_PROJECT_ENVIRONMENT/bin/python" > "$root/experiments/configs/pier-requirements.txt"
"$UV_PROJECT_ENVIRONMENT/bin/pier" run --help > "$root/experiments/configs/pier-run-help.txt"
