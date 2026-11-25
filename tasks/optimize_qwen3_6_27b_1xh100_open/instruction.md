# Optimize Qwen3.6-27B inference in vLLM

The upstream assignment targets the BF16 checkpoint on one H100. The public instruction specifies the source edit policy, workload definitions and scoring. [Original instruction at the pinned revision](https://github.com/apple-aiml-research/ml-rsi-inference-bench/blob/1a38072fbe284234c874356b86c9df666a5a79a3/tasks/optimize_qwen3_6_27b_1xh100_open/instruction.md)

The additional A100 experiment asks whether the unchanged engine completes public correctness and paired timing with the original checkpoint split across two devices. Use the full input lengths, output lengths, concurrency profiles and repetition policy on both arms.
