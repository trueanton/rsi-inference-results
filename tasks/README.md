# H100 task cards

| Pinned Apple task | Target | Agent submission |
| --- | --- | --- |
| [`optimize_qwen3_6_27b_1xh100_open`](optimize_qwen3_6_27b_1xh100_open/) | Qwen3.6-27B BF16, 1 × H100, TP=1 | [Frozen patch](../docs/evidence/h100/qwen/candidate.patch) |
| [`optimize_gpt_oss_120b_2xh100_open`](optimize_gpt_oss_120b_2xh100_open/) | GPT-OSS-120B MXFP4 experts, 2 × H100, TP=2 | [Frozen patch](../docs/evidence/h100/gpt/candidate.patch) |

[H100 optimization report](../docs/findings.md) · [H100 baseline qualification](../docs/h100.md) · [Historical A100 campaign](../docs/a100.md)

The task-local `results/h100/<run-id>/` directories hold H100 qualification records. The top-level `docs/evidence/h100/` directory holds the later optimization records. The task-local `environment/pins/`, `solution/` and original `results/` files document the historical A100 campaign.
