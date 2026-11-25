# Acceptance records

For the A100 campaign, the original server-side audit checked every archived measurement against the workload definition, including the counts of completed requests, input and output tokens. The CSV exports preserve one row per timed repetition and the original evidence filename. Both arms ran unmodified engine code.

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

The fresh GPT verifier ran under the same experiment operator. The campaign contains no external hardware replication. The [machine-readable outcome table](outcomes.csv) records the A100 configuration and verification outcomes and the two H100 qualifications; paths in its throughput column are relative to the repository root.

## Evidence and scope

Each A100 task record publishes the original public `bench.json` and per-prompt `correctness.json`. The `timed-json.zip` beside each CSV contains the original timed JSON files named in its evidence column. The checker matches those files to the CSV, checks both workload arms against the harness output and checks correctness counts against the per-prompt record. The original harness JSON includes its own summary statistics. The descriptive table uses all the observed repetitions and reports sample SD only where it can be calculated. [Qualification and solver-profile variation](variability.md)

The two qualification passes contributed 26 GPT and 18 Qwen rows. A row times one workload/profile on one arm. Warmups, smoke tests, correctness prompts and solver profiling are outside the 9,752 qualification requests. The later GPT solver profiling pass has a separate CSV and raw archive, 13 rows and 2,824 requests per arm. Both passes compared unmodified code. A fresh final-tree verifier checked the solver submission and stopped at the empty-diff gate before candidate performance testing. Its zero reward does not supply a speedup measurement. [Solver profiling CSV](../../tasks/optimize_gpt_oss_120b_2xh100_open/results/solver-profiling/raw-measurements.csv) · [Final verifier metrics](../../tasks/optimize_gpt_oss_120b_2xh100_open/results/verifier-metrics.json)

For the original exit evidence see the [GPT correctness child exits](../../tasks/optimize_gpt_oss_120b_2xh100_open/results/correctness-exits.txt), [H100 hardware preflight on A100](../../tasks/optimize_gpt_oss_120b_2xh100_open/results/native-verifier.txt) and [Qwen recovery record](../../tasks/optimize_qwen3_6_27b_1xh100_open/results/postcheck-recovery.json). The later Qwen postcheck uses the per-workload marker that was present in the historical output. Its correction does not alter any timing or the original Slurm exit status.

To render the descriptive tables directly, run `python3 docs/acceptance/variation.py`. CPU verification uses the published records. Running vLLM, repeating correctness and collecting new timings requires the hardware and procedures in the [GPU reproduction guide](../../RUN.md).

## H100 baseline evidence

The two H100 outcome rows identify the actual Slurm jobs and link to full-precision pristine-arm profile summaries. The CPU checker validates their workload coverage, request counts, units, scheduler identifiers, correctness totals and reported A/A ratios. The checker also rebuilds the A100 display values and compares the report tables with both campaigns’ exports. H100 workload ratios and correctness totals come from the run summaries. The published data allow the geometric mean of the three ratios to be checked. Recomputing those three ratios from timings, or auditing the per-prompt checks and native verifier classifications, requires the original cluster files. [H100 results and evidence scope](../h100.md)
