#!/usr/bin/env bash
set -euo pipefail
umask 077
unset ALL_PROXY all_proxy HTTP_PROXY http_proxy HTTPS_PROXY https_proxy NO_PROXY no_proxy
root=@BENCH_ROOT@
exp="$root/experiments"
target="$root/ml-rsi-inference-bench/tasks/optimize_qwen3_6_27b_1xh100_open/environment"
r="$1"
set -x
date -u
hostname -f
scontrol show job "$SLURM_JOB_ID"
if [[ "$(git -C "$root/ml-rsi-inference-bench" rev-parse HEAD)" != '1a38072fbe284234c874356b86c9df666a5a79a3' ]]; then exit 1; fi
scratch=@LOCAL_ROOT@
mkdir -p "$scratch/builds"
export XDG_RUNTIME_DIR="$scratch/runtime-$SLURM_JOB_ID"
mkdir -m 700 "$XDG_RUNTIME_DIR"
unset DBUS_SESSION_BUS_ADDRESS
export TMPDIR="$scratch/builds/tmp-$SLURM_JOB_ID"
mkdir -m 700 "$TMPDIR"
df -hT @LOCAL_ROOT@ /dev/shm
findmnt -T @LOCAL_ROOT@
podman info --format '{{.Store.GraphRoot}} {{.Store.GraphDriverName}} {{.Host.Security.Rootless}}'
context="$scratch/builds/qwen-$SLURM_JOB_ID"
mkdir "$context"
cp -a "$target"/. "$context/"
patch -d "$context" -p1 < "$exp/patches/setup/qwen-tp2-diagnostic.patch"
python3 -c 'import ast, sys; ast.parse(open(sys.argv[1]).read())' "$context/scripts/_run_benchmark_serve.py"
sha256sum "$context/Dockerfile"
image=localhost/rsi-bench-qwen:0.20.1-sm80-tp2-verified-lock
echo "$image" > "$r/image-name.txt"
podman --cgroup-manager=cgroupfs build --http-proxy=false --no-cache --tag "$image" --file "$context/Dockerfile" "$context"
podman run --rm --pull=never --http-proxy=false --network=none -v "$exp/configs/qwen-upstream-runtime.lock:/expected.lock:ro" -v "$exp/scripts/check-runtime-lock.py:/check-lock.py:ro" "$image" /opt/venv/bin/python3 /check-lock.py /expected.lock > "$r/runtime-lock-audit.json"
podman image inspect "$image" --format '{{.Id}} {{.Size}}' > "$r/image-id-size.txt"
image_archive="$scratch/builds/qwen-$SLURM_JOB_ID.oci.tar"
podman save --format oci-archive --output "$image_archive" "$image"
sha256sum "$image_archive" > "$r/archive.sha256"
printf '%s\n' "$image_archive" > "$r/archive.path"
shared=@SHARED_ROOT@/images
mkdir -p "$shared"
dest="$shared/$(basename "$image_archive")"
test ! -e "$dest"
cp "$image_archive" "$dest.incoming"
expected=$(cut -d' ' -f1 "$r/archive.sha256")
echo "$expected  $dest.incoming" | sha256sum -c -
mv -T "$dest.incoming" "$dest"
echo "$dest" > "$r/shared-archive.path"
date -u
