# GPT-OSS-120B on two A100s

The unchanged vLLM engine served the full MXFP4 checkpoint at tensor parallelism 2. It passed public correctness and completed **5,648 timed requests with zero failures**. The bounded solver left an empty source patch.

## Workload and scores

| Workload | Input tokens | Output tokens | Requests per repetition | Concurrency |
| --- | ---: | ---: | ---: | --- |
| Decode | 1,024 | 8,192 | 4 | 1 |
| Prefill | 8,192 | 1 | 256 | 1 |
| High load | 1,024 | 1,024 | 256 per profile | 16, 32, 64 |

The harness measured two decode boots, five prefill repetitions and two high-load repetitions per profile in each arm. Both arms used the same checkpoint, devices, port settings and 16,384-token context.

| Workload | Unchanged candidate | Pristine | Ratio | Unit |
| --- | ---: | ---: | ---: | --- |
| Decode | 163.70986 | 163.70827 | 1.000010× | tokens/s from median time per output token |
| Prefill | 1.55180 | 1.54626 | 1.003586× | reciprocal seconds from median time to first token |
| High load | 1.36735 | 1.37222 | 0.996447× | geometric mean of requests/s across the three profiles |

The combined self-ratio was **1.000010×**. Each arm completed 2,824 timed requests. The teacher-forced check passed on 1,984 of 2,000 positions over 20 prompts with absolute and relative tolerances of 0.05. [Raw measurements](results/raw-measurements.csv) · [Summary](results/summary.json)

## Port and solver

The stock 80% GPU memory setting left insufficient KV-cache capacity. At 95%, sampler startup still needed 198 MiB with 144 MiB free. Using the 95% setting with `VLLM_MEMORY_PROFILER_ESTIMATE_CUDAGRAPHS=1` allowed 19,168 KV tokens. The A100 runtime selected the Marlin MXFP4 MoE and Triton attention backends. The original verifier withheld its score on A100. [Environment pins](environment/pins/runtime.json) · [Original Apple task](https://github.com/apple-aiml-research/ml-rsi-inference-bench/tree/1a38072fbe284234c874356b86c9df666a5a79a3/tasks/optimize_gpt_oss_120b_2xh100_open)

Mini-SWE-agent 2.4.6 used the open GPT-OSS-120B checkpoint on two separate A100s. The attempt ran for 9,183 seconds of its 30,000-second allowance with medium reasoning and temperature 0.6. The agent completed a second unchanged-engine profile. Its next 32,812-token input exceeded the local 32,768-token context window. A fresh local verifier reproduced the final tree, classified the diff as empty and awarded zero. [Solver evidence](results/solver-result.json) · [Submission](solution/README.md)
