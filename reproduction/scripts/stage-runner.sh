#!/usr/bin/env bash
set -euo pipefail
umask 077
unset ALL_PROXY all_proxy HTTP_PROXY http_proxy HTTPS_PROXY https_proxy NO_PROXY no_proxy
set -x
src=@LOCAL_ROOT@/tools
base=@SHARED_ROOT@/tools
mkdir -p "$base"
# The editable bundled Pier path and the Python 3.12 interpreter have identical paths on compute nodes.
if [[ ! -f "$base/pier-1a38072f.tar.gz" ]]; then
    tar -C "$src" -czf "$base/pier-1a38072f.tar.gz.incoming" pier
    mv "$base/pier-1a38072f.tar.gz.incoming" "$base/pier-1a38072f.tar.gz"
fi
sha256sum "$base/pier-1a38072f.tar.gz"
if [[ ! -f "$base/docker-compose" ]]; then
    curl --fail --location --retry 2 --silent --show-error https://github.com/docker/compose/releases/download/v2.39.4/docker-compose-linux-x86_64 -o "$base/docker-compose.incoming"
    echo "7af95166a730b87e172d4fc9aefea8725d3c6c7327d59149267b452114ddb7d4  $base/docker-compose.incoming" | sha256sum -c -
    chmod 700 "$base/docker-compose.incoming"
    mv "$base/docker-compose.incoming" "$base/docker-compose"
fi
"$base/docker-compose" version
