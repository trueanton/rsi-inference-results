#!/usr/bin/env bash
set -euo pipefail
umask 077
unset ALL_PROXY all_proxy HTTP_PROXY http_proxy HTTPS_PROXY https_proxy NO_PROXY no_proxy
root=@BENCH_ROOT@
exp="$root/experiments"
target="$root/ml-rsi-inference-bench/tasks/optimize_gpt_oss_120b_2xh100_open/environment"
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
context="$scratch/builds/gpt-$SLURM_JOB_ID"
mkdir "$context"
cp -a "$target"/. "$context/"
patch "$context/Dockerfile" < "$exp/patches/setup/gpt-oss-sm80.patch"
sha256sum "$context/Dockerfile"
image=localhost/rsi-bench-gpt-oss:0.19.1-sm80
podman build --http-proxy=false --layers=true --tag "$image" --file "$context/Dockerfile" "$context"
podman image inspect "$image" --format '{{.Id}} {{.Size}}' > "$r/image-id-size.txt"
image_archive="$scratch/builds/gpt-$SLURM_JOB_ID.oci.tar"
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
