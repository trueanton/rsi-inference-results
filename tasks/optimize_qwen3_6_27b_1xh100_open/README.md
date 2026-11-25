# Qwen3.6-27B on 40 GiB A100s

**Assigned single-GPU task:** The 64 transformer layers alone contain 48,706,393,088 BF16 bytes. A 40 GiB device has 42,949,672,960 nominal bytes. That leaves a 5,756,720,128-byte deficit before embeddings, KV cache and workspace.

**Two-GPU diagnostic:** The original BF16 checkpoint completed all three workloads at tensor parallelism 2. Both arms together completed **4,104 timed requests with zero failures**. No solver ran on either configuration. Agent speedup is N/A. [Summary](results/summary.json) · [Original Apple task](https://github.com/apple-aiml-research/ml-rsi-inference-bench/tree/1a38072fbe284234c874356b86c9df666a5a79a3/tasks/optimize_qwen3_6_27b_1xh100_open)

## Workload and scores

| Workload | Input tokens | Output tokens | Requests per repetition | Concurrency |
| --- | ---: | ---: | ---: | --- |
| Decode | 1,024 | 8,192 | 4 | 1 |
| Prefill | 8,192 | 1 | 256 | 1 |
| High load | 1,024 | 1,024 | 256 per profile | 16, 32, 64 |

The harness measured one decode boot, five prefill repetitions and one high-load repetition per profile in each arm. Both arms shared the same two GPUs and used the full 16,384-token serving context.

| Workload | Unchanged candidate | Pristine | Ratio | Unit |
| --- | ---: | ---: | ---: | --- |
| Decode | 42.06380 | 42.07266 | 0.999789× | tokens/s from median time per output token |
| Prefill | 0.83071 | 0.83084 | 0.999841× | reciprocal seconds from median time to first token |
| High load | 0.79511 | 0.79524 | 0.999829× | geometric mean of requests/s across the three profiles |

The combined self-ratio was **0.999820×**. Each arm completed 2,052 timed requests. The teacher-forced correctness check passed on 1,990 of 2,000 positions over 20 prompts with absolute and relative tolerances of 0.05. [Raw measurements](results/raw-measurements.csv)

The single decode observation was 23.77341 ms/token in the candidate arm and 23.76841 in pristine. There is one high-load repetition per concurrency and arm, so those profiles also lack a between-repetition SD. Across five prefill repetitions the means of the median TTFTs were 1,203.78 ms (candidate) and 1,203.74 ms (pristine). The prefill score above uses trimmed reciprocal latencies. [Variation by profile and arm](../../docs/acceptance/variability.md) · [Harness output](results/bench.json)

## Build and audit

The clean image matched all 200 upstream Qwen package pins. Its pip check reported two conflicts with Torch 2.11.0+cu128, for CUDA bindings and toolkit versions. The earlier image and its derivative rebuilds reused GPT dependencies. Their measurements were excluded. [Environment pins](environment/pins/runtime.json) · [Dependency check](results/pip-check.txt)

Both correctness children exited successfully and the benchmark wrote its paired results. Slurm recorded exit 1 after the operator postcheck raised `KeyError: 'mode'`. The Qwen helper records its live pristine baseline per workload. The same operator verified all 18 saved measurements against those records. [Correctness output](results/correctness.json) · [Recovery record](results/postcheck-recovery.json) · [GPU rerun guide](../../RUN.md)
