# Measured environment

The diagnostic kept the Qwen BF16 checkpoint and vLLM runtime at the recorded revisions. Its serving and correctness helpers used two visible A100s at tensor parallelism 2. The source assignment declares TP=1. The clean no-cache image passed the original 200 package pins before these measurements. [Measured pins](pins/runtime.json) · [Upstream environment](https://github.com/apple-aiml-research/ml-rsi-inference-bench/tree/1a38072fbe284234c874356b86c9df666a5a79a3/tasks/optimize_qwen3_6_27b_1xh100_open/environment)

The shared dataset contains the per-repetition results and immutable runtime identifiers. To recheck the published timings from a clone, use the [offline acceptance checker](../../../docs/acceptance/README.md).

[Build, launch and verify the GPU run](../../../RUN.md)
