# Task selection

The assignment comprised two open-ended vLLM optimization tasks from Apple’s benchmark. Each uses a different original checkpoint. The local scheduler offered 40 GiB A100s, so hardware feasibility came before an agent attempt.

| Task | Decision | Evidence |
| --- | --- | --- |
| [GPT-OSS-120B](../../tasks/optimize_gpt_oss_120b_2xh100_open/) | Qualify the original TP=2 checkpoint on A100 and run one bounded agent | Public correctness and all three workloads passed with matched memory settings on both arms. |
| [Qwen3.6-27B](../../tasks/optimize_qwen3_6_27b_1xh100_open/) | Record the assigned TP=1 capacity blocker and measure an additional TP=2 diagnostic | The transformer layers alone exceed one device. Two devices held the BF16 checkpoint and completed the workloads. |

The selection covers these two assigned tasks. Coverage of the other Apple tasks on consumer GPUs is documented in the [companion hardware screen](https://github.com/RefrainTC/RSI_Apple_Bench/tree/5c2a96207c65d81796636c2f31d354e3f04dd65c/docs/selection).
