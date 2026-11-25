# Reproducing the A100 runs

## Check the published evidence on a CPU

From the results repository root, with Python 3.9 or later and no dependencies:

```sh
python3 docs/acceptance/verify_results.py
```

Expected qualification totals are GPT 26 rows / 5,648 requests / 1.000010× and Qwen 18 / 4,104 / 0.999820×. The checker also reads the 26-row GPT solver profiling pass and verifies the fresh-tree evidence. During publication the original operator audit and export scripts also regenerated both qualification CSVs byte-for-byte from the server archives. All four port patches applied to the pinned upstream source. A hardware reproduction builds or loads the pinned runtime and collects new outputs on GPUs. [Calculation method](docs/acceptance/README.md) · [Variation by arm](docs/acceptance/variability.md)

## GPU and storage requirements

| Stage | Allocation used | Slurm wall limit |
| --- | --- | --- |
| Image build, each task | 1 x86-64 CPU node, 8 CPUs, 32 GiB RAM | 2 h |
| GPT public qualification | 2 × A100-SXM4-40GB, 32 CPUs, 240 GiB RAM | 12 h |
| Qwen public diagnostic | 2 × A100-SXM4-40GB, 16 CPUs, 240 GiB RAM | 12 h |
| GPT solver attempt | 4 × A100-SXM4-40GB on one node, 32 CPUs, 240 GiB RAM. Two devices served the target and two served the solver. | 18 h |
| GPT final-tree replay | 2 × A100-SXM4-40GB, 32 CPUs, 240 GiB RAM | 1 h |

The recorded GPUs had 40,960 MiB each, SM80, MIG disabled and driver 570.195.03. Containers had 16 GiB of shared memory. The cluster used Ubuntu 24.04 x86-64, Python 3.12 on the host, Slurm cgroups, rootless Podman 5.4.1 and NVIDIA Container Toolkit CDI. The build needs network access to the pinned sources and packages. The target runs offline. Pier 0.3.0 uses the Docker-compatible Podman socket, Docker CLI 28.5.2 and Compose 2.39.4. The login and compute hosts need the same absolute checkout and virtualenv paths. Compute nodes must see the shared model and image stores.

Both upstream tasks declare 163,840 MiB of container storage. The GPT and Qwen model downloads occupy 65,276,859,410 and 55,586,101,287 bytes respectively. Each has 15 indexed shards. Staging makes a second, hash-verified copy on shared storage. The unpacked images occupy 23,065,049,963 and 24,411,957,786 bytes. Allow additional space for image layers, OCI exports on local and shared storage, build caches, virtualenvs and logs. Peak aggregate disk use was not measured. [Hardware notes](docs/hardware.md) · [File sizes and model hashes](reproduction/configs/models.json)

## Source revisions and port settings

The upstream benchmark commit for both tasks is `1a38072fbe284234c874356b86c9df666a5a79a3`. Each image builds from NVIDIA’s CUDA 12.8.1 Ubuntu 24.04 devel base at manifest `sha256:520292dbb4f755fd360766059e62956e9379485d9e073bbd2f6e3c20c270ed66`.

| | GPT-OSS-120B | Qwen3.6-27B |
| --- | --- | --- |
| Checkpoint | `openai/gpt-oss-120b` at `b5c939de8f754692c1647ca79fbf85e8c1e70f8a` | `Qwen/Qwen3.6-27B` at `1cda14dd71a3f47115850eb790f416f165da1cb5` |
| Engine | vLLM 0.19.1 at `b1388b1fbf5aaef47937fabe98931211684666a6` | vLLM 0.20.1 at `132765e3560659ff63ebd236203672e991b70e08` |
| Torch | 2.10.0+cu128 | 2.11.0+cu128 |
| Target | Original MXFP4, TP=2 | Original BF16, assigned TP=1, measured diagnostic TP=2 |
| Memory fraction, correctness / benchmark | 0.95 / 0.95, `VLLM_MEMORY_PROFILER_ESTIMATE_CUDAGRAPHS=1` | 0.85 / 0.85 |
| Context, correctness / benchmark | 4,096 / 16,384 tokens | 4,096 / 16,384 tokens |
| Public benchmark prompt seed | 1795559967 | 1795580955 |

The image patches pin the base and select SM80. The Qwen patch also makes the public serving helper use both devices. GPT’s public correctness patch exposes the memory fraction. Its separate local evaluator patch changes the allowed GPU type in the task and verifier. The model weights, engine sources and benchmark scoring formula are common to both arms of each comparison. The original GPT H100 hardware gate is exercised separately. [Port patches](reproduction/patches/setup/) · [Upstream license](https://github.com/apple-aiml-research/ml-rsi-inference-bench/blob/1a38072fbe284234c874356b86c9df666a5a79a3/LICENSE) · [GPT pins and archive hashes](tasks/optimize_gpt_oss_120b_2xh100_open/environment/pins/runtime.json) · [Qwen pins and archive hashes](tasks/optimize_qwen3_6_27b_1xh100_open/environment/pins/runtime.json)

## Prepare a fresh cluster workspace

The following Bash commands are a **CPU-validated, GPU-untested relocation** of the recorded procedure. Jobs 434026 and 434291 supplied the build scripts, 434161 and 434292 the qualification evidence, 434294 the solver launcher and 434410 the final verifier launcher. The published public launcher uses the later lock check, stages GPT’s encoding file and understands Qwen’s recorded output schema. On the original GPT run the full 191-pin audit was performed separately on its image. The Qwen build audited 200 pins. Both package audits are published with the task pins. The portable submission wrapper passes the historical prompt seeds explicitly. The environment installers use the archived package freezes and replay reads the rebuilt Pier bundle’s checksum. Site paths, scheduler account, partition and QoS must be supplied locally.

Start in a clone of this results repository. Set three new paths without spaces. Use a shared working filesystem for `BENCH_ROOT`, node-local storage at a consistent path for `LOCAL_ROOT`, and a shared read/write directory for `SHARED_ROOT`. The example paths are placeholders. Choose the site’s CPU or GPU partition, account and QoS through Slurm defaults or `SBATCH_PARTITION`, `SBATCH_ACCOUNT` and `SBATCH_QOS` at the corresponding step.

```bash
set -euo pipefail
unset ALL_PROXY all_proxy HTTP_PROXY http_proxy HTTPS_PROXY https_proxy NO_PROXY no_proxy
export REPORT=$PWD
export BENCH_ROOT=/path/to/shared/workspace LOCAL_ROOT=/path/to/local/scratch SHARED_ROOT=/path/to/shared/assets
export EXP="$BENCH_ROOT/experiments"
mkdir -p "$BENCH_ROOT" "$LOCAL_ROOT" "$SHARED_ROOT"
python3 reproduction/configure.py --bench "$BENCH_ROOT" --local "$LOCAL_ROOT" --shared "$SHARED_ROOT"
git clone https://github.com/apple-aiml-research/ml-rsi-inference-bench.git "$BENCH_ROOT/ml-rsi-inference-bench"
git -C "$BENCH_ROOT/ml-rsi-inference-bench" checkout --detach 1a38072fbe284234c874356b86c9df666a5a79a3
bash "$EXP/scripts/host-tools.sh"
bash "$EXP/scripts/stage-runner.sh"
sha256sum "$SHARED_ROOT/tools/pier-1a38072f.tar.gz" | cut -d' ' -f1 > "$EXP/configs/pier-archive.sha256"
# The CLI staging check expects a rootless Podman socket on the login host.
systemctl --user start podman.socket
bash "$EXP/scripts/stage-docker-cli.sh"
bash "$EXP/scripts/stage-harmony.sh"
py="$LOCAL_ROOT/tools/download-tools/bin/python"
for key in gpt qwen; do
    "$py" "$EXP/scripts/models.py" "$key"
    "$py" "$EXP/scripts/stage-model.py" "$key"
done
"$py" "$EXP/scripts/qwen-capacity.py" > "$EXP/runs/qwen-tp1-capacity.json"
```

The downloader verifies sizes, LFS SHA-256 or Git blob IDs, shard coverage and tokenizer files. The qualification container mounts the staged model read-only at `/models/target`. The capacity report reads safetensors headers. It establishes the single-A100 Qwen memory blocker without running inference.

## Build the images and run qualification

Use the CPU partition for the two builds. Keep these variables for subsequent steps. The builders write the image config ID and unpacked size, archive SHA-256 and shared archive path into each build directory.

```bash
gpt_build=$(mktemp -d "$EXP/runs/gpt-build.XXXXXXXX")
qwen_build=$(mktemp -d "$EXP/runs/qwen-build.XXXXXXXX")
for key in gpt qwen; do
    if [[ $key == gpt ]]; then build=$gpt_build; else build=$qwen_build; fi
    sbatch --wait -N1 -n1 -c8 --mem=32G --time=02:00:00 --output="$build/build-%j.log" \
        "$EXP/scripts/build-$key.sh" "$build"
done
```

Use the GPU partition for the next commands. Set `RSI_GPU_TYPE` if the site uses a different Slurm name for the same A100 model. Run from a persistent login shell. Each wrapper prints its new run directory and watches the live output while the job runs, because later decode boots reuse filenames. Keep the GPT run directory as `GPT_RUN` for the replay below.

```bash
bash "$EXP/scripts/submit-public.sh" gpt "$gpt_build" | tee "$gpt_build/qualification.log"
GPT_RUN=$(head -n 1 "$gpt_build/qualification.log")
bash "$EXP/scripts/submit-public.sh" qwen "$qwen_build" | tee "$qwen_build/qualification.log"
```

Slurm assigns one node and a device pair. The launcher checks the UUIDs inside the rootless CDI container, sets logical CUDA ordinals, uses private IPC/PID namespaces and disables networking. Inspect `gates-<job>.log`, `accounting.txt` and the run’s `logs/agent/`. After the runtime lock and NCCL checks, the recorded in-container commands in `/app` are:

```bash
/opt/venv/bin/python3 /operator/model-smoke.py
/opt/venv/bin/python3 scripts/run_correctness.py --output /logs/agent/correctness.json
/opt/venv/bin/python3 scripts/run_benchmark.py --output /logs/agent/bench.json
```

The wrapper runs `archive-bench.py` while the job is active, then `audit-public.py RUN` and `export-public.py RUN`. Expect `raw-public/index.jsonl`, timestamped raw JSONs, `logs/agent/bench.progress.log`, `public-audit.json`, `raw-measurements.csv` and `public-results.json`. Compare the new scores and raw rows with the historical runs, and record the actual image, driver, seed and tree. GPU timings can vary. During GPT qualification the native `nop` run uses the original verifier. Inspect `native-nop.log`, the Pier job in `native/pier-jobs/` and its verifier output for `gpu_arch_mismatch`. The wrapper permits the public checks to continue even when native verification fails. Confirm the actual native reason separately. [Public launcher](reproduction/scripts/qualification.sh) · [Correctness and benchmark commands](reproduction/scripts/public-gates.sh) · [Original native result](tasks/optimize_gpt_oss_120b_2xh100_open/results/native-verifier.txt)

## Verify the archived GPT submission in a fresh A100 sandbox

This replay needs a qualified GPT run and the staged GPT image but uses **no solver**. The original operator ran it as a separate job after Pier skipped the in-trial verifier. Set `GPT_RUN` and `gpt_build` to the new directories from qualification. The replay checks that the newly built tree matches the archived solver tree and fails on any difference.

```bash
task="$REPORT/tasks/optimize_gpt_oss_120b_2xh100_open"
verify_run=$(mktemp -d "$EXP/runs/gpt-final-tree.XXXXXXXX")
mkdir "$verify_run/frozen" "$verify_run/launcher-source"
cp "$task/solution/candidate-state.txt" "$task/solution/candidate.patch" "$verify_run/frozen/"
# Both archived diffs are zero bytes. Use the same checked empty file for the working-tree diff.
cp "$task/solution/candidate.patch" "$verify_run/frozen/uncommitted.patch"
cp "$EXP/scripts/"{prepare-port.py,prepare-nop.py,cuda-devices.py} "$verify_run/launcher-source/"
cp "$EXP/scripts/verify_empty_tree.py" "$verify_run/launcher-source/frozen_replay.py"
cp -R "$EXP/patches/setup" "$verify_run/launcher-source/setup"
# Write this once in the fresh workspace, using the image actually built there.
python3 - "$EXP/configs/images.json" "$gpt_build" <<'PY'
import json, sys
from pathlib import Path
build = Path(sys.argv[2])
digest = (build / "image-id-size.txt").read_text().split()[0].removeprefix("sha256:")
archive = (build / "shared-archive.path").read_text().strip()
with open(sys.argv[1], "x") as out:
    json.dump({"gpt": {"shared_archive": archive, "image_config_sha256": digest}}, out)
PY
sbatch --wait -N1 -n1 -c32 --gres="gpu:${RSI_GPU_TYPE:-a100-sxm4-40gb}:2" \
    --mem=240G --time=01:00:00 --output="$verify_run/slurm-%j.log" \
    "$EXP/scripts/final-tree-job.sh" "$verify_run" "$GPT_RUN" replay "$verify_run/frozen"
```

Expect the fresh trial under `replay-1/pier-jobs/`, including `agent/replayed-tree.json`, `artifacts/metrics.json` and `verifier/reward.json`. The archived source tree was `a2748086c60be2c6f6f150d02f3a7c0811a65dad`. The historical classification was `empty`, the reason was `no_patch`, and the local reward was 0.0. The different commit IDs in the two sandboxes shared the same tree. The verifier stopped before timing an edited candidate. [Tree proof](tasks/optimize_gpt_oss_120b_2xh100_open/results/solver-result.json) · [Edit-gate output](tasks/optimize_gpt_oss_120b_2xh100_open/results/verifier-metrics.json)

## Historical solver configuration

Job 434294 ran the archived solver launcher with arguments `RUN QUALIFIED_GPT_RUN solver`. It used the same prepared model/image configuration as replay, a separate four-GPU allocation and a dedicated local GPT-OSS-120B service at TP=2. The server command used eager execution, 32,768 context tokens, at most two sequences, 2,048 batched tokens and 0.95 GPU memory utilization. The agent accessed the service through a Unix socket. The target container had no external network access. The run archived an agent log, trajectory, source state, and committed and uncommitted patches under `host-solver/`. The scheduler allocation lasted longer than the individual agent budget.

The published source includes the pinned agent installer, Pier adapter, solver flags and model settings. The controller expects the adapter, `solver-mini.py`, `solver-docker-exec.sh`, `prepare-nop.py`, `prepare-port.py`, `cuda-devices.py` and the setup patches in the run’s `launcher-source/` directory. The historical installer used a separate mini-SWE-agent 2.4.6 environment. Its relocated installer is `bash "$EXP/scripts/stage-solver.sh"`. The solver’s public timing records and final-tree proof are available here. A new solver attempt needs its own configuration and run ID. [Solver launcher](reproduction/scripts/solver-job.sh) · [Agent configuration](reproduction/scripts/solver-mini.py) · [Additional profiling CSV](tasks/optimize_gpt_oss_120b_2xh100_open/results/solver-profiling/raw-measurements.csv) · [Proposed retry](docs/findings.md#proposed-gpt-solver-retry)

## Reproduction limits and future H100 runs

The repository includes setup sources, patches, dependency locks, file-level model hashes, measured OCI identifiers, timed JSONs, correctness outputs and solver/verifier evidence. Checkpoints, OCI tarballs, host virtualenv bundles, package caches, the full solver conversation and full site logs are outside the public release. Rebuilding depends on upstream weights, build inputs and package availability. A different OCI digest is a new build and should be reported with its dependency audit and source tree. No GPU rerun was performed to validate this guide. A complete independent A100 reproduction still requires a compatible cluster and an operator to rebuild or obtain the exact images, rerun both public qualifications and verify the frozen GPT submission.

The H100 campaign on another cluster is pending. For each completed run, use `tasks/<task>/results/h100/<run-id>/` and record GPU model/count, TP, driver, memory settings, source and image revisions, solver configuration, timed rows and the original verifier result. Give each hardware campaign its own outcome and comparison arms. The published A100 qualification and solver history remain at their existing paths.
