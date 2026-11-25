# RSI inference benchmarks on 40 GiB A100s

Can two of Apple’s H100 inference-optimization tasks run on A100s with their original model weights? **GPT-OSS-120B completed the public workloads on two A100s. Qwen3.6-27B exceeded one A100’s memory and completed them on two.** One bounded coding agent attempted the GPT task, exhausted its context, and left an empty patch. A fresh verifier awarded zero optimization credit.

## The tasks

Each ratio compares two copies of the unchanged engine on the same pair of GPUs. A value near 1 measures repeatability. Correctness counts teacher-forced token positions within tolerance across 20 prompts per model.

| Task | Configuration tested | Correct positions | Timed requests | Unchanged ratio | Agent outcome |
| --- | --- | ---: | ---: | ---: | --- |
| [GPT-OSS-120B](tasks/optimize_gpt_oss_120b_2xh100_open/) | Original MXFP4 weights, TP=2, A100 memory settings | 1,984 / 2,000 | 5,648 | 1.000010× | One attempt, verified empty patch |
| [Qwen3.6-27B](tasks/optimize_qwen3_6_27b_1xh100_open/) | Original BF16 weights, separate TP=2 diagnostic | 1,990 / 2,000 | 4,104 | 0.999820× | Assigned TP=1 blocked on memory |

The two qualification runs completed **9,752 timed requests across 44 measurements**, with zero request failures. The GPT agent separately profiled another 5,648 requests on the unchanged engine. The original H100 verifier withheld the GPT score on A100. These are local hardware-port results.

## Check the measurements

From the repository root, run this command with Python 3.9 or later. It recomputes both paired ratios from the per-repetition CSVs, verifies the workload sizes and request totals, and checks the recorded final-tree evidence.

```sh
python3 docs/acceptance/verify_results.py
```

## Repository guide

| Start here | What you’ll find |
| --- | --- |
| [Task index](tasks/README.md) | Task cards, upstream instructions, environment pins, solver outcomes and measurements |
| [Hardware](docs/hardware.md) | GPU capacity, allocation layout, memory settings and cost |
| [Task selection](docs/selection/README.md) | The two assigned tasks and the reason for the extra Qwen diagnostic |
| [Findings](docs/findings.md) | What the results establish and where the measurements stop |
| [Acceptance records](docs/acceptance/README.md) | Correctness, verification, failed setup attempts and the full outcome table |

The experiment uses Apple’s benchmark at revision `1a38072fbe28`. This repository follows the organization of RefrainTC’s consumer-GPU study. That study covers a different set of experiments on RTX hardware. [Upstream benchmark](https://github.com/apple-aiml-research/ml-rsi-inference-bench/tree/1a38072fbe284234c874356b86c9df666a5a79a3) · [Companion RTX study](https://github.com/RefrainTC/RSI_Apple_Bench/tree/5c2a96207c65d81796636c2f31d354e3f04dd65c)
