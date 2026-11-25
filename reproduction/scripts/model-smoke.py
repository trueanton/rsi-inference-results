#!/usr/bin/env python3
import json
import os
from pathlib import Path
import torch
import vllm
import vllm._C
from vllm import LLM, SamplingParams

def main():
    model = os.environ["INFB_MODEL_PATH"]
    case = os.environ["RSI_TARGET"]
    package = Path(vllm.__file__).resolve()
    assert package.is_relative_to(Path("/app/repo").resolve()), package
    print("engine", vllm.__version__, package, "extension", vllm._C.__file__, flush=True)
    print("torch", torch.__version__, "cuda", torch.version.cuda, "nccl", torch.cuda.nccl.version(), flush=True)
    config = json.loads((Path(model)/"config.json").read_text())
    opts = dict(model=model, tensor_parallel_size=2, max_model_len=16384,
                gpu_memory_utilization=float(os.environ.get("RSI_GPT_PORT_MEM","0.80")) if case == "gpt" else 0.85,
                dtype="auto" if case == "gpt" else "bfloat16", trust_remote_code=True,
                enable_prefix_caching=False)
    if case == "qwen":
        assert config["text_config"].get("dtype", config.get("dtype")) == "bfloat16"
        opts.update(limit_mm_per_prompt={"image":0, "video":0}, max_num_seqs=128)
    else:
        assert config["quantization_config"]["quant_method"] == "mxfp4"
    print("smoke options", json.dumps(opts,sort_keys=True), flush=True)
    engine = LLM(**opts)
    out = engine.generate(["The capital city of France is"], SamplingParams(temperature=0, max_tokens=12))
    completion = out[0].outputs[0]
    assert completion.token_ids
    print("smoke completion", json.dumps({"text":completion.text,"token_ids":completion.token_ids}),flush=True)


if __name__ == "__main__":
    main()
