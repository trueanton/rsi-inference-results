# H100 coding-agent optimization

One local GPT-OSS-120B solver attempt ran for each of Apple’s two original H100 inference tasks. Both produced an engine patch. Qwen passed correctness with no measured speedup. GPT-OSS passed native correctness and scored 0.98748× in the official verifier. Its separate verification run was still in progress on 26 November 2026 at 12:18 UTC. [Job accounting](evidence/h100/slurm.csv)

## Targets and baselines

Both targets ran on NVIDIA H100 80 GB HBM3 GPUs on `m2-xe117`, with driver 615.71.09, CUDA 12.8 and Apptainer 1.4.5. The benchmark was pinned to `1a38072fbe284234c874356b86c9df666a5a79a3`. Jobs 543431 and 543515 qualified the unchanged Qwen and GPT engines. Both returned `no_patch` at the native edit gate. These A/A timings establish the starting configurations. [Pinned benchmark](https://github.com/apple-aiml-research/ml-rsi-inference-bench/tree/1a38072fbe284234c874356b86c9df666a5a79a3) · [Qualification evidence and exclusions](h100.md)

| Target | Model checkpoint | vLLM source revision | Qualified runtime |
| --- | --- | --- | --- |
| Qwen3.6-27B BF16, 1 × H100, TP=1 | `1cda14dd71a3f47115850eb790f416f165da1cb5` | `132765e3560659ff63ebd236203672e991b70e08` | vLLM 0.20.1+cu129, Torch 2.11.0+cu128, GPU memory fraction 0.85. [Image, package overrides and tree](../tasks/optimize_qwen3_6_27b_1xh100_open/results/h100/optimize_qwen3_6_27b_1xh100_open_h100_baseline_20261125T103758Z_543431/summary.json) |
| GPT-OSS-120B, MXFP4 experts, 2 × H100, TP=2 | `bc75b44b8a2a116a0e4c6659bcd1b7969885f423` | `b1388b1fbf5aaef47937fabe98931211684666a6` | vLLM 0.19.1, Torch 2.10.0+cu128, GPU memory fraction 0.80. [Image, vocabulary and tree](../tasks/optimize_gpt_oss_120b_2xh100_open/results/h100/optimize_gpt_oss_120b_2xh100_open_h100_baseline_20261125T133721Z_543515/summary.json) |

The GPT qualification decode arms differed by 1.082275× on unchanged code. A follow-up on two H100s matched the measurement phase across the two arms. Both moved from about 200 to 217 output tokens/s within an engine boot. The resulting decode ratio was **0.999959×**. The device-level cause is undetermined. This timing control contributes no agent speedup. [Five measurements per arm, job 545965](evidence/h100/gpt-decode-control.json)

## Solver and budget

The operator selected `openai/gpt-oss-120b` at revision `bc75b44b8a2a116a0e4c6659bcd1b7969885f423` as a separate coding agent for both targets. It ran in eager mode at TP=2 on two additional H100s, with an 8 GiB KV cache per solver GPU, two sequences and 2,048 batched tokens. A custom Python controller sent Harmony chat requests to the local vLLM service. It supplied the pinned public assignment and a developer prompt instructing the agent to profile, edit, test and commit via one Bash tool. The reportable controller versions are the SHA-256 hashes of the actual program used in each segment. Each configuration gives the controller prompt, the URL and verified digest of the exact task prompt, the tool schema and the service arguments. [Qwen solver configuration](evidence/h100/qwen/solver.json) · [GPT solver configuration](evidence/h100/gpt/solver.json)

Each attempt had one **30,000-second wall clock**. The original verifier’s command limit was 18,000 seconds. Generation used medium reasoning, temperature 0.6 and up to 3,072 output tokens inside a 32,768-token context. The controller reserved the output allowance before each request, retained the assignment, recent tool history, last failure and patch state during compaction, and checked service-reported prompt lengths against the actual Harmony renderer. Preflight job 545964 accepted a 29,696-token prompt and rejected 29,697 before generation. Budgeting was by wall time and per-call context. The initial HTTP 500 responses did not return token usage. [Preflight accounting](evidence/h100/slurm.csv) · [Qwen call ledger](evidence/h100/qwen/trajectory.csv) · [GPT call ledger](evidence/h100/gpt/trajectory.csv)

| Target | Delivered replies | Reported prompt / completion tokens | Largest prompt | Seconds from original start to stop |
| --- | ---: | ---: | ---: | ---: |
| [Qwen](evidence/h100/qwen/solver.json) | 411 | 4,037,473 / 110,652 | 24,906 | 29,998 |
| [GPT-OSS](evidence/h100/gpt/solver.json) | 457 | 4,356,624 / 107,569 | 28,453 | 27,621 |

## Attempts, interruptions and operator assistance

The times below are controller start and stop times in UTC. Allocation times include service startup and teardown. Each row after an opening failure continues the same logical attempt, retaining its original deadline. The operator restored files and history and checked the source tree and patch digest before resuming. All solver segments used `m2-xe117`. [Slurm allocation starts, ends and exits](evidence/h100/slurm.csv) · [Qwen segment identities](evidence/h100/qwen/solver.json) · [GPT segment identities](evidence/h100/gpt/solver.json)

| Target | Job | Start → stop (UTC) | What happened |
| --- | ---: | --- | --- |
| Qwen | 545980 | Nov 25 19:47:40 → 19:50:41 | Harmony HTTP 500 on the opening response. Zero delivered replies. |
| Qwen | 546138 | Nov 25 20:07:50 → 20:11:19 | Restarted with 28,789 seconds left. The auxiliary tokenizer returned HTTP 400 after a malformed tool request at step 18. |
| Qwen | 546151 | Nov 25 20:18:46 → Nov 26 04:07:38 | Resumed at step 19 with 28,134 seconds left. The deadline interrupted the final paired benchmark. Slurm recorded `1:0` and the controller retained the working-tree patch. |
| GPT-OSS | 545909 | Nov 25 19:57:41 → 20:00:37 | Harmony HTTP 500 on the opening response. Zero delivered replies. |
| GPT-OSS | 546144 | Nov 25 20:07:45 → 20:56:50 | Restarted with 29,395 seconds left. After step 21 the auxiliary tokenizer rejected malformed tool arguments. |
| GPT-OSS | 546176 | Nov 25 21:00:52 → Nov 26 03:38:01 | Resumed at step 22 with 26,208 seconds left. The agent returned a final answer. Slurm recorded `0:0`. |

The operator added explicit Harmony stop IDs `200002` and `200012` to recover the undelivered opening responses. When malformed arguments broke the secondary tokenizer, the controller preserved the rejected reply on disk, supplied the rejection as text in the next context, and continued to enforce the Harmony count. Neither malformed request executed. During GPT step 13, the agent’s profiling command ran out of GPU memory and hung during NCCL shutdown. After the fatal shutdown message and 904 seconds without more output, the operator signaled that command’s wrapper. It returned 143 and the same controller continued. Setup, recovery delays and the interrupted command consumed time on the original clocks. Human assistance covered the runner, model service, controller, recovery and evaluation. The frozen diffs below are the agent workspaces captured at stop. [Qwen trajectory](evidence/h100/qwen/trajectory.csv) · [GPT trajectory](evidence/h100/gpt/trajectory.csv)

## Qwen submission

The frozen patch changes `vllm/v1/attention/backends/triton_attn.py`, increasing parallel softmax segments from 16 to 32. Its SHA-256 is `a1e40ae3773939c89df436b815b31dc2865519418656c5f2c86b0509ecbe3405`. The native verifier classified it as `source_edit`. All three measured candidate workloads selected FlashAttention 3. The 2–3% gain claimed in the patch comment has no support in these measurements. [Patch](evidence/h100/qwen/candidate.patch) · [Base and replay tree](evidence/h100/qwen/sealed.json) · [Runtime backend selections](evidence/h100/qwen/engine-startups.json)

Job **546421** completed on one H100 with exit `0:0`. The official teacher-forced gate passed **9,903/9,954** positions across 100 prompts. The separate public check passed **1,988/1,997** across 20 prompts. The native verifier awarded **0.0 reward**. Both timing comparisons below completed 2,052 timed requests per arm, with zero failed requests. Correctness was established by the teacher-forced checks. [Official correctness](evidence/h100/qwen/official-correctness.json) · [Public correctness](evidence/h100/qwen/public-correctness.json) · [Native verifier excerpt](evidence/h100/qwen/verifier-excerpt.txt) · [Reward](evidence/h100/qwen/reward.json)

| Candidate / pristine | Decode | Prefill | High load | Overall |
| --- | ---: | ---: | ---: | ---: |
| [Official verifier](evidence/h100/qwen/official.json) | 1.001369× | 0.996191× | 1.001289× | **0.999613×** |
| [Independent repeat 1](evidence/h100/qwen/repeat-1.json) | 1.000880× | 0.998675× | 1.000573× | **1.000042×** |

**Correctness passed; no measured speedup.** These two comparisons provide no confidence interval or equivalence bound. The agent also benchmarked an earlier eight-segment tree during optimization. The table evaluates the frozen 32-segment submission. [Official timed records](evidence/h100/qwen/official-timings.zip) · [Repeat timed records](evidence/h100/qwen/repeat-1-timings.zip)

## GPT submission

The patch sets the default KV block size to **64** in `vllm/config/cache.py`, even though its comment says 32. It sets the default model length to **2,048** in `vllm/engine/arg_utils.py`, enables TF32 matmul and cuDNN benchmarking in `vllm/v1/engine/llm_engine.py`, and adds a short generation script, `test_llm.py`. The serving verifier explicitly supplies a maximum model length of 16,384. The patch SHA-256 is `aeab2417beaa080e9862019a5ca334ae75fb24f6a61ee2e3e601ea6c6097c141`. [Patch](evidence/h100/gpt/candidate.patch) · [Base and replay tree](evidence/h100/gpt/sealed.json) · [Server startup evidence](evidence/h100/gpt/engine-startups.json)

Job **546422** replayed the frozen tree on two H100s. Native correctness passed **9,917/9,918** positions across 100 prompts. The reference process exited on signal 6 after writing its output. The pinned verifier validated the file and continued. The official verifier classified the patch as `mixed` and awarded **0 reward**. Each timed arm finished 2,824 requests with zero failures. The agent’s earlier development measurement used a tree without the final cuDNN setting. Separate verification is in progress. [Official timings](evidence/h100/gpt/official-timings.zip) · [Reward](evidence/h100/gpt/reward.json) · [Native correctness](evidence/h100/gpt/official-correctness.json) · [Verifier excerpt](evidence/h100/gpt/verifier-excerpt.txt) · [Slurm status](evidence/h100/slurm.csv)

| Candidate / pristine | Decode | Prefill | High load | Overall | Completed timed requests / failures |
| --- | --- | --- | --- | --- | --- |
| [Official verifier](evidence/h100/gpt/official.json) | 0.975983× | 0.991077× | 0.995489× | **0.987481×** | 5,648 / 0 |
| Independent repeat | Pending | Pending | Pending | Pending | Pending final record |

All eight measured server startups selected FlashAttention 3 and the Triton MXFP4 MoE backend. Each reported 28.61 GiB available for the KV cache. The candidate allocated capacity for 833,408 tokens and pristine for 833,424, consistent with the change from 16 to 64 tokens per cache block. Both used the verifier’s 16,384-token context. Attribution to an individual edit would require an ablation. [Engine startups](evidence/h100/gpt/engine-startups.json)

## Measurement and artifact access

Each candidate was replayed from its sealed patch against the qualified engine tree. The native verifier ran the pinned task’s original tests. The independent repeat used the public benchmark helper in separate clean workspaces under the same operator, with the same physical GPUs and seed for both arms. In the first repeat, candidate ran before pristine with seed 20261126. The protocol schedules two more pairs for eligible correct submissions, reversing arm order in the second. Later pairs had no published measurements at this snapshot. [First pair design and scores](evidence/h100/qwen/repeat-1.json) · [Qualification workload definitions](h100.md#pristine-arm-throughput-and-latency)

Decode scores inverse median time per output token, and prefill scores inverse median time to first token. High-load scores use the geometric mean of request rates at concurrency 16, 32 and 64. The final ratio is the geometric mean of the three workload ratios. Each decode repetition has only four requests. Order, warmup and the observed GPT timing variation limit interpretation of small differences. [Measurement definitions](acceptance/README.md) · [GPT phase control](evidence/h100/gpt-decode-control.json)

The public evidence includes the exact final patches, tree hashes, verifier excerpts, per-prompt correctness extracts, and the original timed JSONs for completed comparisons. The call ledgers record reported token usage, command exits and snapshot digests. Blank cells mark fields the controller did not record for that step. Full message transcripts, command output logs, intermediate patch contents, controller source and cluster image files are available only to authorized cluster users. [Published evidence index and cluster-relative locators](evidence/h100/README.md)
