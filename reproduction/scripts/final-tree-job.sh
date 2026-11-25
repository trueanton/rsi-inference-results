#!/usr/bin/env bash
set -euo pipefail
umask 077
unset ALL_PROXY all_proxy HTTP_PROXY http_proxy HTTPS_PROXY https_proxy NO_PROXY no_proxy
exp=@BENCH_ROOT@/experiments
r=${1:?run directory}
qualified=${2:?qualified baseline directory}
mode=${3:-solver}
case "$mode" in
    solver) gpu_count=4 ;;
    replay) gpu_count=2; export RSI_FROZEN_ARCHIVE=${4:?frozen archive required} ;;
    *) exit 2 ;;
esac
cd "$exp"
test -s "$qualified/public-audit.json"
python3 - "$qualified/public-audit.json" <<'AUDIT'
import json,sys
d=json.load(open(sys.argv[1]))
assert d["valid"] and d["raw_measurements"]
AUDIT
exec > >(tee -a "$r/controller.log") 2>&1
date -u
scontrol show job "$SLURM_JOB_ID"
scratch=@LOCAL_ROOT@
shared=@SHARED_ROOT@
export XDG_RUNTIME_DIR="$scratch/runtime-$SLURM_JOB_ID"
mkdir -m 700 -p "$XDG_RUNTIME_DIR" "$XDG_RUNTIME_DIR/solver" "$scratch/tools"
unset DBUS_SESSION_BUS_ADDRESS
export PATH="$shared/tools:$scratch/tools/pier/bin:$PATH"
launch="$r/launcher-source"
export PYTHONPATH="$launch"
export DOCKER_CONFIG="$XDG_RUNTIME_DIR/docker-config"
mkdir -p "$DOCKER_CONFIG/cli-plugins"
ln -s "$shared/tools/docker-compose" "$DOCKER_CONFIG/cli-plugins/docker-compose"
export DOCKER_HOST="unix://$XDG_RUNTIME_DIR/pier-api.sock"
export RSI_SOLVER_UDS="$XDG_RUNTIME_DIR/solver/api.sock"
export RSI_SOLVER_ARCHIVE="$r/host-solver"
toolsets=(pier)
if [[ "$mode" == solver ]]; then toolsets+=(mini-swe-agent-2.4.6); fi
for item in "${toolsets[@]}"; do
    if [[ "$item" == pier ]]; then
        filename=pier-1a38072f.tar.gz
        checksum=$(cat "$exp/configs/pier-archive.sha256")
    else
        filename=mini-swe-agent-2.4.6.tar.gz
        checksum=$(cat "$exp/configs/solver-archive.sha256")
    fi
    (
    flock -x 9
    if [[ ! -x "$scratch/tools/$item/bin/python" ]]; then
        echo "$checksum  $shared/tools/$filename" | sha256sum -c -
        incoming=$(mktemp -d "$scratch/tools/incoming.XXXXXX")
        tar -C "$incoming" -xzf "$shared/tools/$filename"
        mv -T "$incoming/$item" "$scratch/tools/$item"
        rmdir "$incoming"
    fi
    ) 9>"$scratch/tools/$item.stage.lock"
done
model=$(python3 -c 'import json;print(json.load(open("configs/volume-map.json"))["gpt"]["shared_host_path"])')
archive=$(python3 -c 'import json;print(json.load(open("configs/images.json"))["gpt"]["shared_archive"])')
digest=$(python3 -c 'import json;print(json.load(open("configs/images.json"))["gpt"]["image_config_sha256"])')
image=localhost/rsi-bench-gpt-oss:0.19.1-sm80
load_image() {
    if ! podman image exists "$digest"; then podman load -i "$archive"; fi
    podman tag "$digest" "$image"
    local current
    current=$(podman image inspect "$image" --format '{{.Id}}')
    [[ "${current#sha256:}" == "$digest" ]]
}
load_image
/usr/bin/python3 "$launch/cuda-devices.py" > "$r/allocated-devices.json"
mapfile -t gpus < <(/usr/bin/python3 - "$r/allocated-devices.json" "$gpu_count" <<'DEV'
import json,sys
d=json.load(open(sys.argv[1]))
assert len(d)==int(sys.argv[2]) and len({x["uuid"] for x in d})==len(d) and all(x["capability"]=="8.0" and x["name"]=="NVIDIA A100-SXM4-40GB" for x in d)
for x in d: print(x["uuid"])
DEV
)
[[ ${#gpus[@]} == "$gpu_count" ]]
target=(--device "nvidia.com/gpu=${gpus[0]}" --device "nvidia.com/gpu=${gpus[1]}")
purposes=(target)
if [[ "$mode" == solver ]]; then
    inference=(--device "nvidia.com/gpu=${gpus[2]}" --device "nvidia.com/gpu=${gpus[3]}")
    purposes+=(inference)
fi
for purpose in "${purposes[@]}"; do
    if [[ "$purpose" == target ]]; then devices=("${target[@]}"); off=0; else devices=("${inference[@]}"); off=2; fi
    podman run --pull=never --rm --network=none --http-proxy=false "${devices[@]}" -e NVIDIA_VISIBLE_DEVICES=void \
        -v "$launch/cuda-devices.py:/gpu-inventory.py:ro" "$digest" env -u CUDA_VISIBLE_DEVICES /opt/venv/bin/python3 /gpu-inventory.py > "$r/$purpose-devices.json"
    python3 - "$r/$purpose-devices.json" "${gpus[off]}" "${gpus[off+1]}" <<'COMPARE'
import json,sys
d=json.load(open(sys.argv[1]))
assert {v["uuid"] for v in d}==set(sys.argv[2:]) and {v["ordinal"] for v in d}=={0,1}
COMPARE
done
nvidia-smi --id="$(IFS=,; echo "${gpus[*]}")" --query-gpu=timestamp,uuid,memory.used,utilization.gpu,clocks.sm,power.draw --format=csv > "$r/gpu-at-start.csv"
podman system service --time=0 "$DOCKER_HOST" > "$r/podman-service.log" 2>&1 &
service=$!
solver_name="rsi-local-solver-$SLURM_JOB_ID"
cleanup() {
    if [[ "$mode" == solver ]]; then podman stop --time 15 "$solver_name" >/dev/null 2>&1 || true; fi
    kill "$service" 2>/dev/null || true
}
trap cleanup EXIT
curl -fsS --retry 15 --retry-delay 1 --retry-all-errors --unix-socket "$XDG_RUNTIME_DIR/pier-api.sock" http://localhost/_ping > "$r/podman-ping.txt"
docker compose version
py="$scratch/tools/pier/bin/python"
if [[ "$mode" == replay ]]; then
    for session in 1; do
        load_image
        out="$r/replay-$session"
        mkdir "$out"
        "$py" "$launch/prepare-port.py" "$out" "$r/target-devices.json" replay
        date -u > "$out/start.utc"
        "$scratch/tools/pier/bin/pier" run -c "$out/a100-port-replay.json" > "$out/pier.log" 2>&1
        date -u > "$out/end.utc"
        python3 - "$out" <<'REPORT'
import json,sys
from pathlib import Path
results=list(Path(sys.argv[1]).glob("pier-jobs/*/*/artifacts/metrics.json"))
if len(results)!=1:
    raise ValueError("Missing replay verifier metrics")
data=json.loads(results[0].read_text())
if data.get("infra_void") or data.get("reason") != "no_patch" or data.get("classification_kind") != "empty":
    raise ValueError(f"Frozen evaluation failed. See {results[0]}")
print("Saved fresh verifier metrics",results[0])
REPORT
    done
    exit 0
fi
mkdir "$r/port-nop" "$r/solver-trial"
"$py" "$launch/prepare-port.py" "$r/port-nop" "$r/target-devices.json" nop
"$scratch/tools/pier/bin/pier" run -c "$r/port-nop/a100-port-nop.json" > "$r/port-nop/pier.log" 2>&1
python3 - "$r/port-nop" <<'NOP'
import json,sys
from pathlib import Path
metrics=list(Path(sys.argv[1]).glob("pier-jobs/*/*/artifacts/metrics.json"))
assert len(metrics)==1,metrics
d=json.loads(metrics[0].read_text())
assert d.get("reason")=="no_patch" or d.get("category_gate_rejected") is True or d.get("classification_kind")=="empty" and not d.get("infra_void"),d.get("reason")
print("Adapted verifier reached its unchanged-source gate",metrics[0])
NOP
load_image
date -u > "$r/solver-server-start.utc"
export RSI_SOLVER_POD_NAME="$solver_name"
podman run --pull=never --name "$solver_name" --rm --http-proxy=false --network=none --pid=private --ipc=private --shm-size=16g \
    "${inference[@]}" -e NVIDIA_VISIBLE_DEVICES=void -e CUDA_VISIBLE_DEVICES=0,1 -e VLLM_USE_AOT_COMPILE=0 \
    -e HF_HUB_OFFLINE=1 -e TRANSFORMERS_OFFLINE=1 -e TIKTOKEN_ENCODINGS_BASE=/runtime/encodings \
    -v "$model:/models/target:ro" -v "$shared/runtime-assets/tiktoken:/runtime/encodings:ro" \
    -v "$XDG_RUNTIME_DIR/solver:/socket:rw" "$digest" \
    /opt/venv/bin/python3 -m vllm.entrypoints.cli.main serve /models/target --served-model-name gpt-oss-120b \
    --uds /socket/api.sock --tensor-parallel-size 2 --dtype auto --max-model-len 32768 --enforce-eager \
    --max-num-seqs 2 --max-num-batched-tokens 2048 --gpu-memory-utilization 0.95 --enable-auto-tool-choice --tool-call-parser openai > "$r/solver-server.log" 2>&1 &
solver_process=$!
curl -fsS --retry 150 --retry-delay 4 --retry-max-time 750 --retry-all-errors --unix-socket "$RSI_SOLVER_UDS" http://localhost/v1/models > "$r/solver-models.json" 2> "$r/solver-startup-retries.log"
"$scratch/tools/mini-swe-agent-2.4.6/bin/python" - "$RSI_SOLVER_UDS" "$r/solver-api-probe.json" <<'PROBE'
import httpx,json,sys
from pathlib import Path
client=httpx.Client(transport=httpx.HTTPTransport(uds=sys.argv[1]),trust_env=False,timeout=180)
tool={"type":"function","function":{"name":"bash","description":"Report a shell command as text.","parameters":{"type":"object","properties":{"command":{"type":"string"}},"required":["command"]}}}
x=client.post("http://localhost/v1/chat/completions",json={"model":"gpt-oss-120b","messages":[{"role":"user","content":"Call the bash tool with the command pwd."}],"tools":[tool],"tool_choice":"auto","max_tokens":512,"temperature":0})
x.raise_for_status()
data=x.json()
Path(sys.argv[2]).write_text(json.dumps(data,indent=2))
toolcall=data["choices"][0]["message"]["tool_calls"][0]["function"]
assert toolcall["name"]=="bash" and isinstance(json.loads(toolcall["arguments"])["command"],str)
print("Local solver API and tool-call protocol verified")
PROBE
"$py" "$launch/prepare-port.py" "$r/solver-trial" "$r/target-devices.json" solver
date -u > "$r/solver-trial/start.utc"
"$scratch/tools/pier/bin/pier" run -c "$r/solver-trial/a100-port-solver.json" > "$r/solver-trial/pier.log" 2>&1
date -u > "$r/solver-trial/end.utc"
nvidia-smi --id="$(IFS=,; echo "${gpus[*]}")" --query-gpu=timestamp,uuid,memory.used,utilization.gpu,clocks.sm,power.draw --format=csv > "$r/gpu-at-end.csv"
date -u
