# RSI inference benchmarks on 40 GiB A100s

We tested two of Apple’s H100 inference optimization tasks on 40 GiB A100s using the original model checkpoints. **GPT-OSS qualified on two A100s. Qwen exceeded the memory of one A100 in its assigned configuration and qualified on two A100s in a separate diagnostic.**

| Task | Original assignment → A100 configuration | Correct positions | Timed requests | A/A ratio | Speedup from a patch | Outcome |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| [GPT-OSS-120B](tasks/optimize_gpt_oss_120b_2xh100_open/) | 2 × H100 TP=2 → 2 × A100 TP=2, MXFP4 | 1,984 / 2,000 | 5,648 | 1.000010× | N/A | Baseline qualified. One optimization attempt reached the context limit before producing a patch. |
| [Qwen3.6-27B](tasks/optimize_qwen3_6_27b_1xh100_open/) | 1 × H100 TP=1 → separate 2 × A100 TP=2 diagnostic, BF16 | 1,990 / 2,000 | 4,104 | 0.999820× | N/A | Assigned TP=1 blocked by memory. TP=2 diagnostic qualified. No optimization attempt. |

Each measured configuration started the model, passed the public teacher-forced correctness check on 20 prompts and completed decode, prefill and high-load serving. The request counts and A/A ratios in the table come from qualification. The two public benchmark passes produced 26 GPT and 18 Qwen timed rows across workloads, concurrency profiles, boots and both comparison arms. Those 44 rows contain 9,752 completed requests and zero request failures. Both arms ran the unchanged engine on the same devices. Their A/A ratios are controls. [Scores and variation by arm](docs/acceptance/variability.md)

After qualification, a separate GPT profiling pass on the unchanged engine added 26 timed rows and 5,648 requests. The next input exceeded the 32,768-token context window, ending the attempt before in-trial verification. The same operator ran the local A100 verifier in a fresh environment. It confirmed the empty diff and awarded **0.0 reward for `no_patch`** before candidate timing. The original H100 verifier withheld a score on A100. [GPT run record](tasks/optimize_gpt_oss_120b_2xh100_open/results/solver-result.json) · [Acceptance and failures](docs/acceptance/README.md)

## Reproduce and extend the results

Run the offline check from a clone with Python 3.9 or later. It compares the CSVs with the original timed JSONs, recomputes the benchmark scores and variability, and checks the correctness and final-tree records.

```sh
python3 docs/acceptance/verify_results.py
```

| Guide | Contents |
| --- | --- |
| [GPU reproduction](RUN.md) | Pinned builds, model downloads, Slurm commands, memory controls and expected outputs |
| [Task index](tasks/README.md) | Task cards, per-workload scores, checkpoints and submissions |
| [Hardware](docs/hardware.md) and [task selection](docs/selection/README.md) | Allocation sizes, costs and rationale for the Qwen diagnostic |
| [Findings](docs/findings.md) | What ran, measurement limitations and the proposed GPT retry |

A separate H100 campaign is in progress on another cluster. Its results are pending. Future runs can be added under `tasks/<task>/results/h100/<run-id>/` with their own pins, raw timings and native verifier output. The A100 campaign has no external independent hardware reproduction.

Apple’s pinned benchmark defines the tasks. The companion study informed the organization of this repository. Each study reports its own experiments. [Upstream benchmark](https://github.com/apple-aiml-research/ml-rsi-inference-bench/tree/1a38072fbe284234c874356b86c9df666a5a79a3) · [Companion study](https://github.com/RefrainTC/RSI_Apple_Bench/tree/5c2a96207c65d81796636c2f31d354e3f04dd65c)
