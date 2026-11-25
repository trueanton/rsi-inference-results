# Optimize GPT-OSS-120B inference in vLLM

Use the public Apple task instructions for the source edit policy, workload definitions and scoring. The original assignment targets two H100s at tensor parallelism 2. [Original instruction at the pinned revision](https://github.com/apple-aiml-research/ml-rsi-inference-bench/blob/1a38072fbe284234c874356b86c9df666a5a79a3/tasks/optimize_gpt_oss_120b_2xh100_open/instruction.md)

For the local hardware port, the task sandbox has two 40 GiB A100s, the original MXFP4 checkpoint and the prepared vLLM source. The agent has one 30,000-second attempt. Measure the public workloads, check correctness, and commit a source change that improves throughput if the evidence supports it. Keep an experiment log and leave a clean working tree.
