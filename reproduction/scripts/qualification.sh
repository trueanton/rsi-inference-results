#!/usr/bin/env bash
set -euo pipefail
umask 077
unset ALL_PROXY all_proxy HTTP_PROXY http_proxy HTTPS_PROXY https_proxy NO_PROXY no_proxy
exp=@BENCH_ROOT@/experiments
key=${1:?target required}
build_run=${2:?build run required}
r=${3:?qualification run required}
if [[ "$key" == qwen ]]; then
    image=localhost/rsi-bench-qwen:0.20.1-sm80-tp2
    high_load=1
else
    [[ "$key" == gpt ]]
    image=localhost/rsi-bench-gpt-oss:0.19.1-sm80
    high_load=2
fi
if [[ -s "$build_run/image-name.txt" ]]; then image=$(cat "$build_run/image-name.txt"); fi
set -x
date -u
hostname -f
scontrol show job "$SLURM_JOB_ID"
test -n "${SLURM_JOB_GPUS:-}"
scratch=@LOCAL_ROOT@
mkdir -p "$scratch"
export XDG_RUNTIME_DIR="$scratch/runtime-$SLURM_JOB_ID"
mkdir -m 700 "$XDG_RUNTIME_DIR"
export TMPDIR="$scratch/tmp-$SLURM_JOB_ID"
mkdir -m 700 "$TMPDIR"
unset DBUS_SESSION_BUS_ADDRESS
mkdir -p "$r/operator" "$r/logs/agent"
for script in cuda-devices.py nccl-probe.py model-smoke.py public-gates.sh; do cp "$exp/scripts/$script" "$r/operator/"; done
if [[ "$key" == gpt ]]; then mkdir -p "$r/operator/encodings"; cp @SHARED_ROOT@/runtime-assets/tiktoken/o200k_base.tiktoken "$r/operator/encodings/"; fi
cp "$exp/configs/$key-upstream-runtime.lock" "$r/operator/expected-runtime.lock"
cp "$exp/scripts/check-runtime-lock.py" "$r/operator/"
python3 "$r/operator/cuda-devices.py" > "$r/allocated-devices.json"
uuids=$(python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); assert len(d)==2 and all(i["capability"]=="8.0" for i in d), d; print(",".join(i["uuid"] for i in d))' "$r/allocated-devices.json")
nvidia-smi -L
nvidia-smi topo -m
df -hT @LOCAL_ROOT@ /dev/shm
archive=$(cat "$build_run/shared-archive.path")
digest=$(cut -d' ' -f1 "$build_run/image-id-size.txt")
model=$(python3 -c 'import json,pathlib,sys; d=json.load(open(sys.argv[1]))[sys.argv[2]]; print(pathlib.Path("@SHARED_ROOT@/models")/d["repo"].split("/")[1]/d["revision"])' "$exp/configs/models.json" "$key")
test -s "$model/.rsi-verified.json"
local_id=$(podman image inspect "$image" --format '{{.Id}}' 2>/dev/null || :)
if [[ "${local_id#sha256:}" != "${digest#sha256:}" ]]; then podman load -i "$archive"; fi
local_id=$(podman image inspect "$image" --format '{{.Id}}')
[[ "${local_id#sha256:}" == "${digest#sha256:}" ]]
# CDI selectors use scheduler-visible UUIDs or the corresponding physical index reported by NVML.
devices=()
cdi=$(command -v nvidia-ctk || :)
if [[ -n "$cdi" ]]; then
    "$cdi" cdi list > "$r/cdi-list.txt" 2>&1 || :
    if ! grep -q 'nvidia.com/gpu=' "$r/cdi-list.txt"; then
        mkdir "$XDG_RUNTIME_DIR/cdi"
        "$cdi" cdi generate --output="$XDG_RUNTIME_DIR/cdi/nvidia.yaml"
        export CONTAINERS_CONF_OVERRIDE="$XDG_RUNTIME_DIR/cdi.conf"
        printf '[engine]\ncdi_spec_dirs = ["%s/cdi"]\n' "$XDG_RUNTIME_DIR" > "$CONTAINERS_CONF_OVERRIDE"
        "$cdi" cdi list --spec-dirs "$XDG_RUNTIME_DIR/cdi" > "$r/cdi-list.txt" 2>&1 || :
    fi
fi
IFS=, read -r -a allocated <<< "$uuids"
for u in "${allocated[@]}"; do
    n=$(nvidia-smi --id="$u" --query-gpu=index --format=csv,noheader,nounits)
    if [[ -f "$r/cdi-list.txt" ]] && grep -Fxq "nvidia.com/gpu=$u" "$r/cdi-list.txt"; then
        devices+=(--device "nvidia.com/gpu=$u")
    else
        devices+=(--device "nvidia.com/gpu=$n")
    fi
done
# Slurm/cgroup supplies resource limits to the job, and Podman supplies private PID, IPC and network namespaces.
args=(--rm --http-proxy=false --network=none --pid=private --ipc=private --shm-size=16g
      "${devices[@]}" -v "$model:/models/target:ro" -v "$r/operator:/operator:ro" -v "$r/logs:/logs:rw"
      -e "RSI_TARGET=$key" -e "RSI_ALLOCATED_UUIDS=$uuids" -e "CUDA_VISIBLE_DEVICES=$uuids"
      -e "INFB_BENCH_SEED=${INFB_BENCH_SEED:?set the public workload seed}" -e INFB_MODEL_PATH=/models/target -e INFB_CORRECTNESS_TP=2
      -e INFB_WORKLOAD_NUM_RUNS_DECODE_HEAVY=1 -e INFB_WORKLOAD_NUM_RUNS_PREFILL_HEAVY=5
      -e "INFB_WORKLOAD_NUM_RUNS_HIGH_LOAD=$high_load" -e HF_HUB_OFFLINE=1 -e TRANSFORMERS_OFFLINE=1)
nvidia-smi --id="$uuids" --query-gpu=timestamp,uuid,memory.used,utilization.gpu,clocks.sm,power.draw --format=csv -l 5 > "$r/gpu-samples-5s.csv" &
sampler=$!
trap 'kill "$sampler" 2>/dev/null || true' EXIT
if [[ "$key" == gpt && "${RSI_GPT_PORT_MEM:-}" == 0.95 ]]; then
    cp "$exp/patches/setup/gpt-public-correctness-memory.patch" "$r/operator/"
    podman run --rm --http-proxy=false --network=none --ipc=private --pid=private "${devices[@]}" -v "$r/operator:/operator:ro" -e NVIDIA_VISIBLE_DEVICES=void "$image" env -u CUDA_VISIBLE_DEVICES python3 /operator/cuda-devices.py > "$r/cdi-preflight.json"
    python3 - "$r/cdi-preflight.json" "$uuids" <<'COMPARE'
import json, sys
assert {d["uuid"] for d in json.load(open(sys.argv[1]))}==set(sys.argv[2].split(","))
COMPARE
    if [[ -n "${RSI_NATIVE_EVIDENCE:-}" ]] && grep -q 'INFRA-VOID preflight=gpu_arch_mismatch' "$RSI_NATIVE_EVIDENCE"; then
        echo "$RSI_NATIVE_EVIDENCE" > "$r/original-verifier-evidence.path"
    else
        native_rc=0
        bash "$exp/scripts/native-nop.sh" "$r" "$r/cdi-preflight.json" > "$r/native-nop.log" 2>&1 || native_rc=$?
        echo "$native_rc" > "$r/native-nop.exit"
    fi
    if ! podman image exists "$digest"; then podman load -i "$archive"; fi
    post_id=$(podman image inspect "$digest" --format '{{.Id}}')
    [[ "${post_id#sha256:}" == "${digest#sha256:}" ]]
    args+=(-e RSI_GPT_PORT_MEM=0.95 -e INFB_DIAG_GPU_MEM_UTIL=0.95 -e INFB_CORRECTNESS_GPU_MEM_UTIL=0.95)
    if [[ "${RSI_GPT_PROFILE_GRAPHS:-0}" == 1 ]]; then args+=(-e VLLM_MEMORY_PROFILER_ESTIMATE_CUDAGRAPHS=1); fi
fi
podman run --pull=never "${args[@]}" "$digest" /bin/bash /operator/public-gates.sh
date -u
