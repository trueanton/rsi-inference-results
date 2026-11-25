#!/usr/bin/env bash
set -euo pipefail
unset ALL_PROXY all_proxy HTTP_PROXY http_proxy HTTPS_PROXY https_proxy NO_PROXY no_proxy
umask 077
run=$1
cdi_inventory=$2
exp=@BENCH_ROOT@/experiments
shared=@SHARED_ROOT@/tools
tools=@LOCAL_ROOT@/tools
mkdir -p "$tools" "$run/native" "$XDG_RUNTIME_DIR/docker-config/cli-plugins"
if [[ ! -x "$tools/pier/bin/pier" ]]; then tar -C "$tools" -xzf "$shared/pier-1a38072f.tar.gz"; fi
export PATH="$shared:$tools/pier/bin:$PATH"
export DOCKER_CONFIG="$XDG_RUNTIME_DIR/docker-config"
ln -s "$shared/docker-compose" "$DOCKER_CONFIG/cli-plugins/docker-compose"
export DOCKER_HOST="unix://$XDG_RUNTIME_DIR/rsi-podman.sock"
podman system service --time=0 "$DOCKER_HOST" > "$run/native/podman-service.log" 2>&1 &
service=$!
trap 'kill "$service" 2>/dev/null || true' EXIT
for i in {1..30}; do if [[ -S "$XDG_RUNTIME_DIR/rsi-podman.sock" ]]; then break; fi; sleep 1; done
set -x
docker info --format '{{.OSType}}'
docker compose version
"$tools/pier/bin/python" "$exp/scripts/prepare-nop.py" "$run/native" "$cdi_inventory"
"$tools/pier/bin/pier" run -c "$run/native/native-nop.json"
