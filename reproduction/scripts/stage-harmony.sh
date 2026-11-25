#!/usr/bin/env bash
set -euo pipefail
unset ALL_PROXY all_proxy HTTP_PROXY http_proxy HTTPS_PROXY https_proxy NO_PROXY no_proxy
umask 077
set -x
dir=@SHARED_ROOT@/runtime-assets/tiktoken
mkdir -p "$dir"
name=o200k_base.tiktoken
expected=446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d
if [[ ! -e "$dir/$name" ]]; then
    curl -fsSL --retry 2 "https://openaipublic.blob.core.windows.net/encodings/$name" -o "$dir/$name.incoming"
    echo "$expected  $dir/$name.incoming" | sha256sum -c -
    mv "$dir/$name.incoming" "$dir/$name"
fi
echo "$expected  $dir/$name" | sha256sum -c -
