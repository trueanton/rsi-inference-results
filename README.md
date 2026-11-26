# Coding-agent optimization on H100

A local GPT-OSS-120B coding agent attempted Apple’s original Qwen3.6-27B task on **1 × H100** and GPT-OSS-120B task on **2 × H100**. A custom offline controller gave the solver one Bash tool and a 30,000-second budget per task. Two additional H100s served the solver in each attempt. [Solver configuration and recovery history](docs/findings.md#solver-and-budget)

## Results

Snapshot on 26 November 2026 at 11:36 UTC. The official column records Apple’s pinned verifier running on our cluster. The repeat compares the frozen patch with a freshly timed pristine engine in a separate measurement by the same operator. Ratios above 1 favor the patch.

| Task and target | Solver | Frozen patch | Official correctness | Official speedup | Separate repeat | Outcome |
| --- | --- | --- | --- | ---: | ---: | --- |
| [Qwen3.6-27B · 1 × H100](tasks/optimize_qwen3_6_27b_1xh100_open/) | GPT-OSS-120B | [Triton softmax segments](docs/evidence/h100/qwen/candidate.patch) | [Passed · 9,903/9,954](docs/evidence/h100/qwen/official-correctness.json) | [0.99961×](docs/evidence/h100/qwen/official.json) | [1.00004×](docs/evidence/h100/qwen/repeat-1.json) | Correctness passed; no measured speedup. |
| [GPT-OSS-120B · 2 × H100](tasks/optimize_gpt_oss_120b_2xh100_open/) | GPT-OSS-120B | [Cache and engine defaults](docs/evidence/h100/gpt/candidate.patch) | [Passed · 9,917/9,918](docs/evidence/h100/gpt/official-correctness.json) | Pending | Pending | [Performance verification running, job 546422](docs/evidence/h100/slurm.csv). |

Earlier qualification jobs timed unchanged engines and returned `no_patch`. The later agent attempts each produced a nonempty submission. Request completion, teacher-forced correctness and performance are reported separately. [Optimization report and workload scores](docs/findings.md) · [Baseline qualification](docs/h100.md)

## Apple’s externally reported results

Apple’s pinned leaderboard lists **1.385×** for Sonnet-5.5 on the Qwen task and **1.382×** for Opus-5.5 on the GPT-OSS task. Our runs used a different solver. We have not independently reproduced those leaderboard submissions. [Apple leaderboard at the benchmark revision](https://github.com/apple-aiml-research/ml-rsi-inference-bench/blob/1a38072fbe284234c874356b86c9df666a5a79a3/docs/leaderboard.html)

## Check the evidence

```sh
python3 docs/acceptance/verify_results.py
```

[Task cards](tasks/README.md) · [Acceptance checks](docs/acceptance/README.md) · [Historical A100 campaign](docs/a100.md)
