#!/usr/bin/env bash
# Submit one qualification and archive raw files while the public harness is running.
set -euo pipefail
unset ALL_PROXY all_proxy HTTP_PROXY http_proxy HTTPS_PROXY https_proxy NO_PROXY no_proxy
umask 077
exp=@BENCH_ROOT@/experiments
key=${1:?gpt or qwen}
build=${2:?completed image build directory}
test -s "$build/shared-archive.path"
case "$key" in
    gpt)
        task=optimize_gpt_oss_120b_2xh100_open
        classification=hardware_port
        cpus=32
        export RSI_GPT_PORT_MEM=0.95 RSI_GPT_PROFILE_GRAPHS=1 INFB_BENCH_SEED=1795559967
        ;;
    qwen)
        task=optimize_qwen3_6_27b_1xh100_open
        classification=diagnostic_variant
        cpus=16
        unset RSI_GPT_PORT_MEM RSI_GPT_PROFILE_GRAPHS
        export INFB_BENCH_SEED=1795580955
        ;;
    *) exit 2 ;;
esac
unset RSI_NATIVE_EVIDENCE
run=$(mktemp -d "$exp/runs/$key-qualification.XXXXXXXX")
printf '%s\n' "$run"
cp "$exp/scripts/qualification.sh" "$run/submitted.sh"
python3 - "$run" "$task" "$classification" <<'PY'
import json, sys
from pathlib import Path
run, task, classification = sys.argv[1:]
(Path(run) / "manifest.json").write_text(json.dumps(dict(task=task, classification=classification)) + "\n")
PY
sbatch --parsable -N1 -n1 -c"$cpus" --gres="gpu:${RSI_GPU_TYPE:-a100-sxm4-40gb}:2" \
    --mem=240G --time=12:00:00 --output="$run/gates-%j.log" \
    "$run/submitted.sh" "$key" "$build" "$run" | cut -d';' -f1 > "$run/job-id"
python3 "$exp/scripts/archive-bench.py" "$run"
# The watcher can outlive Slurm's controller record. Keep both accounting and public evidence.
sacct -j "$(cat "$run/job-id")" --format=JobID,State,ExitCode,Elapsed > "$run/accounting.txt"
python3 "$exp/scripts/audit-public.py" "$run"
python3 "$exp/scripts/export-public.py" "$run"
