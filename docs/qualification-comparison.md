# Historical A100–H100 qualification comparison

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

Both runs used two GPUs at TP=2 and the same vLLM source tree. The two model revisions have identical hashes for all 15 weight shards and differ in their generation defaults. A100 used 95% GPU memory utilization and Marlin MXFP4. H100 used 80% and Triton MXFP4. [Checkpoint and runtime details](h100.md#setup-and-evidence)

| Workload | Metric | 2 × A100 | 2 × H100 |
| --- | --- | ---: | ---: |
| Decode, c1 | Time per output token (ms/token) ↓ | 6.11 | 5.00 |
| Prefill, c1 | Time to first token (ms) ↓ | 646.72 | 163.98 |
| High load, c16 | Requests/s ↑ | 1.1415 | 1.9348 |
| High load, c32 | Requests/s ↑ | 1.5029 | 3.0272 |
| High load, c64 | Requests/s ↑ | 1.5062 | 4.5528 |

At concurrency 64 the H100 pair served 3.02× as many requests per second as the A100 pair. That ratio compares the two complete serving configurations. Within the H100 run itself, the unchanged arms differed by 8.23% on the decode score. A later phase-matched unchanged-code control measured 0.999959×. The underlying system cause is undetermined. [H100 control measurements](h100.md#interpreting-the-paired-results)

### Tail latency

At concurrency 64, p99 time to first token was **46.28 s on A100 and 20.11 s on H100** for the Qwen configurations above. For GPT-OSS it was **24.63 s and 1.31 s**, respectively. The separate reports give p95 and p99 at every measured concurrency. [A100 tail latency](a100.md#tail-latency) · [H100 tail latency](h100.md#tail-latency)
