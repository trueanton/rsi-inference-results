#!/usr/bin/env python3
import collections
import json
from pathlib import Path
import struct

root=Path("@BENCH_ROOT@/experiments")
model=json.loads((root/"configs/models.json").read_text())["qwen"]
usage=collections.Counter()
types=collections.Counter()
for shard in model["indexed_shards"]:
    with (Path(model["destination"])/shard).open("rb") as stream:
        header_bytes=struct.unpack("<Q",stream.read(8))[0]
        header=json.loads(stream.read(header_bytes))
    for name,tensor in header.items():
        if name=="__metadata__":
            continue
        start,end=tensor["data_offsets"]
        if name.startswith("model.language_model.layers."):
            group="language_transformer_layers"
        elif name.startswith("model.language_model."):
            group="language_embeddings_and_norm"
        elif name.startswith("lm_head."):
            group="language_output_head"
        elif name.startswith("model.visual."):
            group="vision"
        elif name.startswith("mtp."):
            group="mtp"
        else:
            raise ValueError(name)
        usage[group]+=end-start
        if group=="language_transformer_layers":
            types[tensor["dtype"]]+=end-start
assert sum(usage.values())==model["index_weight_bytes"]
gpu_mib=40960
lower_bound=usage["language_transformer_layers"]
assert lower_bound > gpu_mib*2**20
print(json.dumps(dict(task="optimize_qwen3_6_27b_1xh100_open",status="blocked",tp=1,
    repo=model["repo"],revision=model["revision"],data_bytes_by_component=usage,
    language_layer_bytes_by_dtype=types,device_memory_mib=gpu_mib,historical_hardware_probe_job=434000,
    minimum_excess_bytes_before_embeddings_or_cache=lower_bound-gpu_mib*2**20,
    checkpoint_index_bytes=model["index_weight_bytes"]),indent=2))
