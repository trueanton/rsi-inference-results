# RSI inference benchmarks on A100 and H100

**[A100 results](docs/a100.md)** · **[H100 results](docs/h100.md)**

**Both of Apple’s original inference tasks ran on their assigned H100 hardware.** Qwen3.6-27B ran on one 80 GB H100 at tensor parallelism 1 (TP=1). GPT-OSS-120B ran on two 80 GB H100s at TP=2. Both passed public correctness and completed all three public serving workloads. The H100 campaign tested the unchanged baselines. The original verifier recorded `no_patch` for each, so speedup from a patch is N/A.

The A100 campaign ran the same public workloads on 40 GiB GPUs. GPT required different memory settings. Qwen exceeded the capacity of one A100 and qualified separately on two. Each hardware report links to its own run records.

## Side-by-side comparison

The tables compare the pristine arm of each qualification run. Concurrency (c) is the maximum number of requests in flight. Both campaigns used the same benchmark revision, input/output lengths and repetitions per model. The prompt seeds differed between clusters. Prefill latency averages the middle three of five repetition medians. The arrows show the favorable direction for each metric.

### Qwen3.6-27B · BF16

One 40 GiB A100 could not fit the checkpoint. The A100 column uses the two-GPU diagnostic at TP=2. The H100 column uses the assigned single 80 GB GPU at TP=1. Both ran the same checkpoint revision.

| Workload | Metric | 2 × A100 | 1 × H100 |
| --- | --- | ---: | ---: |
| Decode, c1 | Time per output token (ms/token) ↓ | 23.77 | 20.52 |
| Prefill, c1 | Time to first token (ms) ↓ | 1,203.60 | 711.19 |
| High load, c16 | Requests/s ↑ | 0.5200 | 0.6477 |
| High load, c32 | Requests/s ↑ | 0.8716 | 1.1171 |
| High load, c64 | Requests/s ↑ | 1.1096 | 1.4641 |

At concurrency 64 the H100 configuration served 1.32× as many requests per second. At concurrency 16 and 32 it also served more requests per second, but requests waited longer for their first token. At concurrency 16, for example, median TTFT was 525 ms on the A100 pair and 1,022 ms on the H100.

### GPT-OSS-120B · MXFP4

Both runs used two GPUs at TP=2 and the same vLLM source tree. The two model revisions have identical hashes for all 15 weight shards and differ in their generation defaults. A100 used 95% GPU memory utilization and Marlin MXFP4. H100 used 80% and Triton MXFP4. [Checkpoint and runtime details](docs/h100.md#setup-and-evidence)

| Workload | Metric | 2 × A100 | 2 × H100 |
| --- | --- | ---: | ---: |
| Decode, c1 | Time per output token (ms/token) ↓ | 6.11 | 5.00 |
| Prefill, c1 | Time to first token (ms) ↓ | 646.72 | 163.98 |
| High load, c16 | Requests/s ↑ | 1.1415 | 1.9348 |
| High load, c32 | Requests/s ↑ | 1.5029 | 3.0272 |
| High load, c64 | Requests/s ↑ | 1.5062 | 4.5528 |

At concurrency 64 the H100 pair served 3.02× as many requests per second as the A100 pair. That ratio compares the two complete serving configurations. Within the H100 run itself, the unchanged arms differed by 8.23% on the decode score. The cause remains open. [H100 control measurements](docs/h100.md#interpreting-the-paired-results)

## Reproduce and extend the results

Run the offline check from a clone with Python 3.9 or later. For A100 it compares the CSVs with the archived timed JSONs and checks scores, correctness and final-tree records. For H100 it checks the exported profile summaries and the arithmetic of the reported paired ratios. It also checks the numbers in the side-by-side and hardware report tables.

```sh
python3 docs/acceptance/verify_results.py
```

| Guide | Contents |
| --- | --- |
| [A100 GPU reproduction](RUN.md) | Pinned builds, model downloads, Slurm commands, memory controls and expected outputs |
| [Task index](tasks/README.md) | Task cards, per-workload scores, checkpoints and submissions |
| [Hardware](docs/hardware.md) and [task selection](docs/selection/README.md) | Allocation sizes, costs and rationale for the Qwen diagnostic |
| [Findings](docs/findings.md) | What ran, measurement limitations and the proposed GPT retry |

The A100 rerun guide applies to the A100 port. The H100 campaign used Slurm and Apptainer with the original H100 assignments. [H100 setup and measurements](docs/h100.md)

Apple’s pinned benchmark defines the tasks. The companion study informed the organization of this repository. Each study reports its own experiments. [Upstream benchmark](https://github.com/apple-aiml-research/ml-rsi-inference-bench/tree/1a38072fbe284234c874356b86c9df666a5a79a3) · [Companion study](https://github.com/RefrainTC/RSI_Apple_Bench/tree/5c2a96207c65d81796636c2f31d354e3f04dd65c)
