# Measured environment

The pin file identifies the engine commit, model snapshot, OCI image configuration digest and runtime used for both measurement arms. The image digest identifies the experiment build. The upstream environment directory contains the original H100 build recipe, public workloads and server entry points. [Measured pins](pins/runtime.json) · [Upstream environment](https://github.com/apple-aiml-research/ml-rsi-inference-bench/tree/1a38072fbe284234c874356b86c9df666a5a79a3/tasks/optimize_gpt_oss_120b_2xh100_open/environment)

For the A100 port, both arms used tensor parallelism 2, a 16,384-token server context, native MXFP4 weights, 95% GPU memory utilization and CUDA graph memory estimation. The same operator ran the final-tree verifier in a fresh sandbox with a local A100 hardware check. The checkout’s original H100 verifier was also run and recorded separately. To recheck the published timings from a clone, use the [offline acceptance checker](../../../docs/acceptance/README.md).

[Build, launch and verify the GPU run](../../../RUN.md)
