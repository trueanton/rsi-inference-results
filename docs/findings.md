# Findings

**The original GPT-OSS-120B checkpoint runs at TP=2 on two 40 GiB A100s.** At the original 80% memory setting the engine reported a 4.24 GiB deficit for KV cache. At 95% the sampler still ran out of memory during startup. Charging CUDA graph memory against that same budget let both arms complete the full workloads. The self-comparison was 1.000010×. [GPT task card](../tasks/optimize_gpt_oss_120b_2xh100_open/)

**For Qwen3.6-27B, GPU count determines feasibility.** The 64 transformer layers require 48,706,393,088 BF16 bytes before embeddings, KV cache and workspace. The TP=2 diagnostic retained the weights and scored 0.999820× across the three public workloads. [Qwen task card](../tasks/optimize_qwen3_6_27b_1xh100_open/)

**The agent produced no source-level improvement in its single attempt.** After profiling GPT-OSS, its next request exceeded the configured context window by 44 tokens. The final working tree was clean and identical to its baseline. An independent run of the local verifier reproduced the tree and returned `no_patch`. The experiment provides no edited candidate for a speedup estimate. [Verifier evidence](../tasks/optimize_gpt_oss_120b_2xh100_open/results/solver-result.json)

**Two measurement issues affected interpretation.** An earlier Qwen image reused GPT dependencies and was excluded. In the corrected run the final postcheck expected a GPT-only JSON field. The saved Qwen measurements passed a subsequent per-workload audit. GPT correctness also produced complete artifacts before its two child processes exited on signal 6 during teardown. [Acceptance record](acceptance/README.md)
