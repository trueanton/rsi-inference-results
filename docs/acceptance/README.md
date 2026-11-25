# Acceptance records

The original server-side audit checked every archived measurement against the workload definition, including the counts of completed requests, input and output tokens. The CSV exports preserve one row per timed repetition and the original evidence filename. Both arms ran unmodified engine code.

## Recompute the published results

```sh
python3 docs/acceptance/verify_results.py
```

Run from the repository root with Python 3.9 or later. The checker verifies the recorded request counts, token counts, concurrency and repetitions. It computes the decode score as 1,000 divided by median time per output token in milliseconds, and the prefill score as 1,000 divided by median time to first token in milliseconds. For high load it takes the geometric mean of requests/s at concurrency 16, 32 and 64 within each repetition. With at least three repetition scores, the harness drops the minimum and maximum before averaging. The final ratio is the geometric mean of the three workload ratios.

## Outcomes and exceptions

| Stage | Evidence and interpretation |
| --- | --- |
| GPT public correctness | 1,984 of 2,000 positions within tolerance. Both child processes wrote their outputs and exited on signal 6 during teardown. The upstream helper accepted the artifacts. |
| GPT native verifier | The declared H100 hardware check returned `gpu_arch_mismatch` and withheld a native score. |
| GPT final local verifier | The in-trial verifier was skipped on the agent process error. A fresh sandbox reproduced the archived tree and awarded zero at the edit-category gate. |
| Qwen image build | An earlier cached build had the GPT dependency lock. Its measurements were excluded. The clean stock build matched all 200 original Qwen pins. |
| Qwen diagnostic | 1,990 of 2,000 positions within tolerance. Both correctness children exited successfully. The public benchmark wrote its full paired output. A later operator postcheck raised `KeyError: 'mode'`, producing Slurm exit 1. The recovery audit used each workload’s live pristine marker and verified all 18 raw files. |

The fresh GPT verifier ran under the same experiment operator. The campaign contains no external hardware replication. The [machine-readable outcome table](outcomes.csv) records the eight configuration and verification outcomes; paths in its throughput column are relative to the repository root.
