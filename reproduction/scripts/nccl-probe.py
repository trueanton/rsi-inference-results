#!/usr/bin/env python3
import os
import torch
import torch.distributed as dist

rank = int(os.environ["LOCAL_RANK"])
torch.cuda.set_device(rank)
dist.init_process_group(backend="nccl")
assert dist.get_world_size() == 2
value = torch.tensor([float(rank+1)], device=f"cuda:{rank}")
dist.all_reduce(value)
assert value.item() == 3.0
print("rank", rank, "device", torch.cuda.get_device_name(rank), "all_reduce_sum", value.item(), flush=True)
dist.destroy_process_group()
