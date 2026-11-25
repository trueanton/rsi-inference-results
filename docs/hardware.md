# Hardware and runtime

The measured A100 target in each run occupied two NVIDIA A100-SXM4 GPUs with 40 GiB each, compute capability 8.0 and driver 570.195.03. Slurm allocated the devices. The containers selected the allocated GPU UUIDs and checked them against their visible CUDA devices. Both arms of each paired comparison ran on the same physical devices.

| Stage | Target GPUs | Solver GPUs | Allocated GPU-hours | Peak MiB per target device |
| --- | ---: | ---: | ---: | ---: |
| GPT-OSS baseline | 2 | 0 | 5.070 | 39,893 |
| Qwen diagnostic | 2 | 0 | 7.299 | 35,403 |
| GPT-OSS agent allocation | 2 | 2 | 10.822 | Start and end snapshots only |
| GPT-OSS final tree verification | 2 | 0 | 0.097 | — |

The campaign used **23.969 allocated GPU-hours** including setup probes and failed runs. The qualification sampler recorded device memory every five seconds. Each benchmark container had a 16 GiB shared-memory allocation. The scheduled host-memory request was 240 GiB. CPU allocations were 32 cores for the GPT task and 16 for Qwen.

The checkpoints were mounted read-only. The agent executed shell commands in an offline sandbox and used a separate, local GPT-OSS inference service. Exact checkpoint, engine and image identifiers are in the [GPT environment](../tasks/optimize_gpt_oss_120b_2xh100_open/environment/pins/runtime.json) and [Qwen environment](../tasks/optimize_qwen3_6_27b_1xh100_open/environment/pins/runtime.json).

## H100 allocations

Job 543431 used one H100 80GB HBM3 and 16 CPUs for Qwen TP=1. Job 543515 used two of the same GPU model and 32 CPUs for GPT-OSS TP=2. Each allocation requested 256 GiB of host RAM and used a private 16 GiB shared-memory filesystem. The driver was 615.71.09. [H100 image identifiers, settings and wall times](h100.md)
