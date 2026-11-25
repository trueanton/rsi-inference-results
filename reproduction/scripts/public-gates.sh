#!/usr/bin/env bash
set -euo pipefail
unset ALL_PROXY all_proxy HTTP_PROXY http_proxy HTTPS_PROXY https_proxy NO_PROXY no_proxy
cd /app
mkdir -p /logs/agent /logs/artifacts /logs/verifier
exec > >(tee /logs/agent/gates.log) 2>&1
set -x
if [[ "$RSI_TARGET" == gpt && -s /operator/encodings/o200k_base.tiktoken ]]; then export TIKTOKEN_ENCODINGS_BASE=/operator/encodings; fi
# Environment declared by the pinned task.toml for public runs.
export INFB_EDIT_POLICY_CSRC=1
export INFB_EDIT_POLICY_CSRC_DEPS=1
export INFB_AGENT_TIMEOUT_SEC=30000
export INFB_VLLM_PYTHON=/opt/venv/bin/python3
export INFB_WORKLOAD_NUM_RUNS_DECODE_HEAVY=1
export INFB_WORKLOAD_NUM_RUNS_PREFILL_HEAVY=5
export MAX_JOBS=8
export VLLM_USE_AOT_COMPILE=0
if [[ "$RSI_TARGET" == gpt ]]; then
    export INFB_EDIT_POLICY_PKGS=triton_kernels
    export INFB_WORKLOAD_NUM_RUNS_HIGH_LOAD=2
else
    export INFB_WORKLOAD_NUM_RUNS_HIGH_LOAD=1
fi
date -u
cat /sys/fs/cgroup/memory.max || true
df -h /dev/shm /app /models/target
nvidia-smi --query-gpu=uuid,name,memory.total,driver_version --format=csv,noheader
python3 /operator/cuda-devices.py > /logs/agent/container-devices.json
python3 - <<'PY'
import json, os, subprocess
d=json.load(open('/logs/agent/container-devices.json'))
expected=set(os.environ['RSI_ALLOCATED_UUIDS'].split(','))
observed={entry['uuid'] for entry in d}
assert len(expected)==2 and len(d)==2 and observed==expected,(d,expected)
nvml=set(subprocess.check_output(['nvidia-smi','--query-gpu=uuid','--format=csv,noheader'],text=True).split())
assert nvml==expected, (nvml,expected)
PY
# Pinned vLLM converts CUDA_VISIBLE_DEVICES entries to integers. CDI already
# attached only the allocated UUIDs. Resolve their ordinals inside this namespace.
env -u CUDA_VISIBLE_DEVICES python3 /operator/cuda-devices.py > /logs/agent/cdi-devices.json
CUDA_VISIBLE_DEVICES=$(python3 - <<'ORDINALS'
import json, os
devices=json.load(open('/logs/agent/cdi-devices.json'))
ordinals={d['uuid']: d['ordinal'] for d in devices}
expected=os.environ['RSI_ALLOCATED_UUIDS'].split(',')
assert set(ordinals) == set(expected) and len(devices)==2, (devices,expected)
print(','.join(str(ordinals[u]) for u in expected))
ORDINALS
)
export CUDA_VISIBLE_DEVICES
python3 /operator/cuda-devices.py > /logs/agent/logical-devices.json
python3 - <<'CHECK'
import json, os
observed=[d['uuid'] for d in json.load(open('/logs/agent/logical-devices.json'))]
assert observed==os.environ['RSI_ALLOCATED_UUIDS'].split(','), observed
CHECK
if [[ "${RSI_GPT_PORT_MEM:-}" == 0.95 ]]; then
    patch -d /app/scripts -p1 < /operator/gpt-public-correctness-memory.patch
fi
/opt/venv/bin/python3 /operator/check-runtime-lock.py /operator/expected-runtime.lock > /logs/agent/runtime-lock-audit.json
bash /app/scripts/pier_healthcheck.sh
git -C /app/repo rev-parse HEAD inference_base > /logs/agent/baseline-refs.txt
test "$(git -C /app/repo rev-parse HEAD)" = "$(git -C /app/repo rev-parse inference_base)"
git -C /app/repo diff --exit-code inference_base --
export PYTHONPATH=/app/repo
if [[ -d /app/.flashinfer_overlay ]]; then PYTHONPATH=/app/.flashinfer_overlay:$PYTHONPATH; fi
py=/opt/venv/bin/python3
if [[ "$RSI_TARGET" == qwen ]]; then
    "$py" -c 'from pathlib import Path; import hashlib,torch,vllm._C; p=Path(vllm._C.__file__).resolve(); print("active core extension",p,hashlib.file_digest(p.open("rb"),"sha256").hexdigest(),torch.ops._C.silu_and_mul_per_block_quant.default)'
    "$py" -c 'from pathlib import Path; import hashlib,torch,vllm._C_stable_libtorch as ext; p=Path(ext.__file__).resolve(); print("companion extension",p,hashlib.file_digest(p.open("rb"),"sha256").hexdigest(),torch.ops._C.cutlass_scaled_mm_supports_fp8(80))'
fi
"$py" -m pip freeze > /logs/agent/installed.txt
"$py" -m pip check > /logs/agent/pip-check.txt 2>&1 || cat /logs/agent/pip-check.txt
"$py" -m torch.distributed.run --standalone --nproc_per_node=2 /operator/nccl-probe.py
if [[ "$RSI_TARGET" == gpt && "${RSI_GPT_PORT_MEM:-}" == 0.95 && "${VLLM_MEMORY_PROFILER_ESTIMATE_CUDAGRAPHS:-0}" == 1 ]]; then
    # Replay the pinned public server's default startup with the full task environment.
    # A successful default startup selects the original policy for the remaining public gates.
    rc=0
    env -u VLLM_MEMORY_PROFILER_ESTIMATE_CUDAGRAPHS -u RSI_GPT_PORT_MEM -u INFB_DIAG_GPU_MEM_UTIL -u INFB_CORRECTNESS_GPU_MEM_UTIL "$py" - <<'DEFAULT_SERVE' || rc=$?
import json, os, sys
from pathlib import Path
sys.path.insert(0,"/app/scripts")
import _run_benchmark_serve as bench
port=bench._pick_free_port()
log=Path("/logs/agent/original-default-serve.log")
process=bench._start_vllm_serve(model=os.environ["INFB_MODEL_PATH"],venv_python="/opt/venv/bin/python3",repo=Path("/app/repo"),port=port,log_path=log,cuda_devices=os.environ["CUDA_VISIBLE_DEVICES"])
try:
    ready=bench._wait_for_server_ready(port,1800,process)
    details=dict(ready=ready,server_rc=process.poll(),memory_fraction=0.80)
    Path("/logs/agent/original-default-startup.json").write_text(json.dumps(details,indent=2))
finally:
    bench._stop_vllm_serve(process)
if not ready:
    sys.exit(42 if "No available memory for the cache blocks" in log.read_text(errors="replace") else 1)
DEFAULT_SERVE
    case "$rc" in
        0) unset VLLM_MEMORY_PROFILER_ESTIMATE_CUDAGRAPHS RSI_GPT_PORT_MEM INFB_DIAG_GPU_MEM_UTIL INFB_CORRECTNESS_GPU_MEM_UTIL ;;
        42) echo "Original public server confirmed the KV-cache capacity blocker. Continuing with graph-aware 95 percent." ;;
        *) echo "Inspect original-default-serve.log before continuing"; exit "$rc" ;;
    esac
fi
"$py" /operator/model-smoke.py
date -u
"$py" scripts/run_correctness.py --output /logs/agent/correctness.json
date -u
"$py" scripts/run_benchmark.py --output /logs/agent/bench.json
date -u
"$py" - <<'PY'
import json, math
from pathlib import Path
summary=json.loads(Path("/logs/agent/bench.json").read_text())
public=json.loads(Path("/app/public/workloads.json").read_text())["workloads"]
# Qwen records paired mode on each workload via baseline_source. GPT also records mode at the root.
import os
if os.environ["RSI_TARGET"]!="qwen" or "mode" in summary:
    assert summary.get("mode")=="paired"
assert set(summary["per_workload"])=={w["name"] for w in public}
for spec in public:
    name=spec["name"]
    row=summary["per_workload"][name]
    assert row["baseline_source"]=="live_pristine", row["baseline_source"]
    assert all(row["workload"].get(k)==spec.get(k) for k in ("input_len","output_len","num_prompts","max_concurrency","profiles")), name
    expected=summary["num_runs"][name]*summary["boots"][name]
    for side in ("candidate_runs","pristine_runs"):
        runs=row[side]
        assert len(runs)==expected and all(math.isfinite(x) and x>0 for x in runs), (name,side,expected,runs)
    assert row["speedup"] and math.isfinite(row["speedup"]) and row["speedup"]>0, name
print("All public paired workloads returned the expected number of positive measurements.")
PY
