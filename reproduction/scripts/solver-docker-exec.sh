#!/usr/bin/env bash
set -euo pipefail
unset ALL_PROXY all_proxy HTTP_PROXY http_proxy HTTPS_PROXY https_proxy NO_PROXY no_proxy
[[ "$1" == exec ]]
shift
exec @SHARED_ROOT@/tools/docker exec --user "$RSI_SOLVER_SANDBOX_UID" "$@"
