#!/usr/bin/env bash
set -euo pipefail
unset ALL_PROXY all_proxy HTTP_PROXY http_proxy HTTPS_PROXY https_proxy NO_PROXY no_proxy
umask 077
set -x
tools=@SHARED_ROOT@/tools
scratch=@LOCAL_ROOT@/tools
pkg="$scratch/docker-ce-cli_28.5.2_amd64.deb"
url='https://download.docker.com/linux/ubuntu/dists/noble/pool/stable/amd64/docker-ce-cli_28.5.2-1~ubuntu.24.04~noble_amd64.deb'
if [[ ! -f "$pkg" ]]; then curl -fsSL --retry 2 "$url" -o "$pkg"; fi
echo "a8b99bc3f4adf30f4a267a01e53979fc691a56b9aa42dbb8576b7c457fa8f2a5  $pkg" | sha256sum -c -
mkdir -p "$scratch/docker-cli-28.5.2"
dpkg-deb -x "$pkg" "$scratch/docker-cli-28.5.2"
if [[ ! -e "$tools/docker" ]]; then install -m 700 "$scratch/docker-cli-28.5.2/usr/bin/docker" "$tools/docker"; fi
cmp "$scratch/docker-cli-28.5.2/usr/bin/docker" "$tools/docker"
export DOCKER_HOST="unix:///run/user/$(id -u)/podman/podman.sock"
export DOCKER_CONFIG="$scratch/docker-config"
mkdir -p "$DOCKER_CONFIG/cli-plugins"
if [[ ! -e "$DOCKER_CONFIG/cli-plugins/docker-compose" ]]; then ln -s "$tools/docker-compose" "$DOCKER_CONFIG/cli-plugins/docker-compose"; fi
"$tools/docker" --version
"$tools/docker" compose version
"$tools/docker" info --format '{{.OSType}}'
