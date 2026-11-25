# Tasks

Both tasks use the original model checkpoint and the pinned vLLM engine. Tensor parallelism (TP) is the number of GPUs that share one copy of the model.

| Apple task | Assigned | Measured A100 configuration | A100 evidence |
| --- | --- | --- | --- |
| [GPT-OSS-120B](optimize_gpt_oss_120b_2xh100_open/) | 2 × H100, TP=2 | 2 × A100, TP=2 | [Qualification summary](optimize_gpt_oss_120b_2xh100_open/results/summary.json) · [Solver result](optimize_gpt_oss_120b_2xh100_open/results/solver-result.json) |
| [Qwen3.6-27B](optimize_qwen3_6_27b_1xh100_open/) | 1 × H100, TP=1 | 2 × A100, TP=2 diagnostic | [Qualification and capacity summary](optimize_qwen3_6_27b_1xh100_open/results/summary.json) |

In each directory, `README.md` is the task card, `task.toml` identifies the experiment, and `instruction.md` points to the original public solver assignment. `environment/pins/` records the measured runtime, `results/` contains the evidence, and `solution/` records what was submitted. The [acceptance checker](../docs/acceptance/README.md) reads both tasks’ results.

Both assigned H100 configurations qualified in a separate baseline campaign. [H100 workload results](../docs/h100.md) · [Qwen H100 run](optimize_qwen3_6_27b_1xh100_open/results/h100/optimize_qwen3_6_27b_1xh100_open_h100_baseline_20261125T103758Z_543431/summary.json) · [GPT-OSS H100 run](optimize_gpt_oss_120b_2xh100_open/results/h100/optimize_gpt_oss_120b_2xh100_open_h100_baseline_20261125T133721Z_543515/summary.json)
