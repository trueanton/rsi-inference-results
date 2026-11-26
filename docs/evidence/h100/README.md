# H100 optimization evidence

The Qwen and GPT directories hold the two frozen submissions from campaign `control-and-solver-20261125T170216Z-rJWV`. The files in this snapshot were exported while GPT job 546422 was running. [Optimization report](../../findings.md) · [Allocation accounting in UTC](slurm.csv)

| Record | Qwen | GPT-OSS |
| --- | --- | --- |
| Exact frozen patch and source trees | [Patch](qwen/candidate.patch) · [Trees](qwen/sealed.json) | [Patch](gpt/candidate.patch) · [Trees](gpt/sealed.json) |
| Solver settings, prompt provenance, controller hashes and budgets | [Configuration](qwen/solver.json) | [Configuration](gpt/solver.json) |
| Step-by-step reply and patch-digest ledger | [CSV](qwen/trajectory.csv) | [CSV](gpt/trajectory.csv) |
| Official correctness and verifier log excerpt | [Correctness](qwen/official-correctness.json) · [Log](qwen/verifier-excerpt.txt) | [Correctness](gpt/official-correctness.json) · [Log](gpt/verifier-excerpt.txt) |
| Official performance and reward | [Scores](qwen/official.json) · [Timed JSONs](qwen/official-timings.zip) · [Reward](qwen/reward.json) | Pending |
| Separate public correctness and repeat | [Correctness](qwen/public-correctness.json) · [Scores](qwen/repeat-1.json) · [Timed JSONs](qwen/repeat-1-timings.zip) | Pending |

Correctness and official score extracts carry the SHA-256 of their complete source JSON. The ZIPs contain the original timed JSON bytes. Both reply ledgers omit conversation text and model reasoning. The solver records include the digest of each distinct intermediate diff. The final patches retain the agent’s original comments, including unverified claims.

## Cluster-only records

Authorized operators can resolve these paths relative to `~/research/bench/rsi-inference-experiments/20261124T195642Z/runs/control-and-solver-20261125T170216Z-rJWV/`. Substitute the full Apple task ID for `<task>`. These private files have no public download URL.

| Record | Relative path |
| --- | --- |
| Messages, commands, original output and intermediate patch blobs | `{trials,recovery-trials,checkpoint-trials}/<task>/solver/host/controller/` |
| Runtime identity, controller source and recovery evidence | `checkpoint-trials/<task>/solver/{model/service.json,host-programs/,continuity.json}` |
| Full native verifier logs, metrics and raw timings | `checkpoint-trials/<task>/verify-1/official/{measurement.log,logs/artifacts/,logs/verifier/}` |
| Public correctness, repeat arms and raw score audits | `checkpoint-trials/<task>/verify-1/{correctness,candidate,pristine}/` |
| Setup and unchanged-code investigation | `operator/setup-record.md`, `gpt-order-control/finding.md`, `gpt-phase-control/run-545965/` |
