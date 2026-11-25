# RSI inference benchmarks on A100 and H100

Both original H100 assignments qualified. Qwen3.6-27B ran on one H100 and GPT-OSS-120B ran on two. Every timed request completed across both unchanged-engine arms.

| H100 baseline | Slurm job | Correct positions | Timed requests, both arms | A/A ratio |
| --- | ---: | ---: | ---: | ---: |
| Qwen3.6-27B, TP=1 | 543431 | 1,994 / 2,000 | 4,104 | 0.993442× |
| GPT-OSS-120B, TP=2 | 543515 | 2,000 / 2,000 | 5,648 | 1.030606× |

The H100 campaign covered baseline qualification. The native verifier returned `no_patch` for both tasks. GPT-OSS showed an 8.23% decode difference between unchanged arms across two boots per arm. [H100 throughput, latency and run records](docs/h100.md)

## A100 port and optimization attempt

We tested two of Apple’s H100 inference optimization tasks on 40 GiB A100s using the original model checkpoints. **GPT-OSS qualified on two A100s. Qwen exceeded the memory of one A100 in its assigned configuration and qualified on two A100s in a separate diagnostic.**

| Task | Original assignment → A100 configuration | Correct positions | Timed requests | A/A ratio | Speedup from a patch | Outcome |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| [GPT-OSS-120B](tasks/optimize_gpt_oss_120b_2xh100_open/) | 2 × H100 TP=2 → 2 × A100 TP=2, MXFP4 | 1,984 / 2,000 | 5,648 | 1.000010× | N/A | Baseline qualified. One optimization attempt reached the context limit before producing a patch. |
| [Qwen3.6-27B](tasks/optimize_qwen3_6_27b_1xh100_open/) | 1 × H100 TP=1 → separate 2 × A100 TP=2 diagnostic, BF16 | 1,990 / 2,000 | 4,104 | 0.999820× | N/A | Assigned TP=1 blocked by memory. TP=2 diagnostic qualified. No optimization attempt. |

Each measured configuration started the model, passed the public teacher-forced correctness check on 20 prompts and completed decode, prefill and high-load serving. The request counts and A/A ratios in the table come from qualification. The two public benchmark passes produced 26 GPT and 18 Qwen timed rows across workloads, concurrency profiles, boots and both comparison arms. Those 44 rows contain 9,752 completed requests and zero request failures. Both arms ran the unchanged engine on the same devices. Their A/A ratios are controls. [Scores and variation by arm](docs/acceptance/variability.md)

After qualification, a separate GPT profiling pass on the unchanged engine added 26 timed rows and 5,648 requests. The next input exceeded the 32,768-token context window, ending the attempt before in-trial verification. The same operator ran the local A100 verifier in a fresh environment. It confirmed the empty diff and awarded **0.0 reward for `no_patch`** before candidate timing. The original H100 verifier withheld a score on A100. [GPT run record](tasks/optimize_gpt_oss_120b_2xh100_open/results/solver-result.json) · [Acceptance and failures](docs/acceptance/README.md)

## Reproduce and extend the results

Run the offline check from a clone with Python 3.9 or later. For A100 it compares the CSVs with the archived timed JSONs and checks scores, correctness and final-tree records. For H100 it checks the exported profile summaries, workload coverage and reported paired ratios against the outcome table.

```sh
python3 docs/acceptance/verify_results.py
```

| Guide | Contents |
| --- | --- |
| [GPU reproduction](RUN.md) | Pinned builds, model downloads, Slurm commands, memory controls and expected outputs |
| [Task index](tasks/README.md) | Task cards, per-workload scores, checkpoints and submissions |
| [Hardware](docs/hardware.md) and [task selection](docs/selection/README.md) | Allocation sizes, costs and rationale for the Qwen diagnostic |
| [Findings](docs/findings.md) | What ran, measurement limitations and the proposed GPT retry |

The A100 rerun guide applies to the A100 port. The H100 campaign used Slurm and Apptainer with the original H100 assignments. [H100 setup and measurements](docs/h100.md)

Apple’s pinned benchmark defines the tasks. The companion study informed the organization of this repository. Each study reports its own experiments. [Upstream benchmark](https://github.com/apple-aiml-research/ml-rsi-inference-bench/tree/1a38072fbe284234c874356b86c9df666a5a79a3) · [Companion study](https://github.com/RefrainTC/RSI_Apple_Bench/tree/5c2a96207c65d81796636c2f31d354e3f04dd65c)
