# Findings

## H100 baseline outcome

Both tasks qualified on the assigned GPU counts. The Qwen single-H100 result establishes that the full BF16 checkpoint and all public workloads fit in the assigned configuration. The GPT run completed MXFP4 inference across two H100s. Its unchanged first arm averaged 216.14 output tokens/s in heavy decode, while the pristine arm averaged 199.61. The source tree was clean and the cause of this difference remains unresolved. [H100 measurements and run records](h100.md)

## A100 baseline outcome

**GPT-OSS-120B ran at TP=2 with the original MXFP4 weights.** The 80% memory budget left a 4.24 GiB KV-cache deficit on the A100 pair. At 95% the sampler still ran out of memory during startup. Accounting for CUDA graph memory within the 95% budget let both arms start and finish the public tests. The benchmark measured the same engine on both sides. Its prefill ratio was 1.003586× and its high-load ratio was 0.996447×. Their opposing deviations largely cancel in the 1.000010× geometric mean. The per-arm repetition data are the basis for describing variability. [GPT task card](../tasks/optimize_gpt_oss_120b_2xh100_open/) · [Repetition statistics](acceptance/variability.md)

**The assigned Qwen3.6-27B TP=1 configuration exceeded device capacity.** Its BF16 language layers alone occupy 48,706,393,088 bytes on a device with 42,949,672,960 nominal bytes. The separately qualified TP=2 diagnostic retained the full checkpoint and completed 4,104 timed requests at an A/A ratio of 0.999820×. The single observations for decode and each high-load concurrency in each arm leave their between-repetition variability unknown. [Qwen task card](../tasks/optimize_qwen3_6_27b_1xh100_open/)

**The only agent attempt ended before candidate evaluation.** Its own GPT profiling pass added 26 timed rows. The next input exceeded the solver context window by 44 tokens. The in-trial verifier was skipped. A fresh A100 sandbox run by the same operator reproduced the clean tree and awarded 0.0 reward for an empty diff. Agent speedup is N/A. The original GPT verifier, invoked separately on A100, withheld an H100 score. No external researcher has independently reproduced this A100 campaign on hardware. [Solver and tree proof](../tasks/optimize_gpt_oss_120b_2xh100_open/results/solver-result.json) · [Original verifier output](../tasks/optimize_gpt_oss_120b_2xh100_open/results/native-verifier.txt)

**Three exceptions affect interpretation.** GPT’s two correctness children exited on signal 6 after writing the outputs the public helper accepted. The first Qwen image and its derivative rebuilds carried the wrong dependency lock and were excluded. On the clean Qwen image the public benchmark finished, then an operator postcheck failed. A recovery audit matched all 18 raw records to the declared workloads and their live pristine comparisons. [Acceptance and exclusions](acceptance/README.md)

## Proposed GPT solver retry

This experiment is planned. The original unsuccessful attempt remains the reference record.

1. Assign a new run ID. Preserve the qualified checkpoint, engine tree, image digest, TP=2 target, 95% memory settings, workload definitions and baseline artifacts. Record the target/solver GPU split. Match the original two target GPUs plus two solver GPUs when comparing attempts.
2. Exercise context management on a saved history before allocating GPUs. Count the rendered prompt including tool schemas and observations, reserve completion space and test a near-limit input. Check that the agent can use its history after summarization, retain the current diff and experimental results, and stop with an explicit reason when the remaining input cannot fit.
3. Record the solver model and revision, agent version, system prompt, config diff, context and output limits, temperature, reasoning effort, time/token budgets, retry policy and stop conditions. The original used mini-SWE-agent 2.4.6, the pinned local GPT-OSS-120B model, 32,768 context tokens, up to 3,072 output tokens, temperature 0.6, medium reasoning, 30,000 s for the agent and 18,000 s for verification. Treat any history-handling or budget change as part of the new experiment.
4. Save the trajectory, token usage and stop reason. After each attempted edit, save the intermediate patch and its base tree, including edits later reverted. Freeze the final committed and working-tree diffs.
5. Reconstruct the final tree in a fresh environment. Record the edit classification, correctness and paired workload timings for a qualifying candidate. Report local verifier reward separately from measured speedup and preserve negative or empty outcomes.
