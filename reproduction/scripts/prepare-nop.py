#!/usr/bin/env python3
"""Prepare an operator-only Pier run using the original GPT-OSS verifier."""
import argparse
import json
from pathlib import Path
import shutil
import uuid

from pier.models.job.config import JobConfig
import yaml

def prepare(run: Path, devices: Path) -> Path:
    root=Path("@BENCH_ROOT@")
    task_id="optimize_gpt_oss_120b_2xh100_open"
    src=root/"ml-rsi-inference-bench"/"tasks"/task_id
    volumes=json.loads((root/"experiments/configs/volume-map.json").read_text())
    container_devices=json.loads(devices.read_text())
    gpu_ids=[item["uuid"] for item in container_devices]
    ordinals=[item["ordinal"] for item in container_devices]
    if set(ordinals)!={0,1}:
        raise ValueError("Pass the two-device CDI inventory captured inside the container")
    if len(set(gpu_ids)) != 2 or len(gpu_ids)!=2:
        raise ValueError("The original GPT-OSS verifier requires two allocated GPUs")
    for g in gpu_ids:
        assert g.startswith("GPU-") and str(uuid.UUID(g[4:]))==g[4:]
    task=run/"operator-task"/task_id
    task.mkdir(parents=True)
    shutil.copy2(src/"instruction.md",task/"instruction.md")
    shutil.copytree(src/"environment", task/"environment",symlinks=True)
    shutil.copytree(src/"tests", task/"tests",symlinks=True)
    image="localhost/rsi-bench-gpt-oss:0.19.1-sm80"
    original=(src/"task.toml").read_text()
    assert original.count("[environment]\n")==1 and "docker_image =" not in original
    (task/"task.toml").write_text(original.replace("[environment]\n",f'[environment]\ndocker_image = "{image}"\n',1))
    # The port overrides only the count-based Compose reservation. CDI attaches the two
    # verified UUIDs. The on-disk and in-memory task configurations still declare two GPUs.
    service={"devices":[f"nvidia.com/gpu={g}" for g in gpu_ids],
             "environment":{"CUDA_VISIBLE_DEVICES":",".join(map(str,ordinals)),
                            "NVIDIA_VISIBLE_DEVICES":"void","INFB_MODEL_PATH":"/models/target",
                            "HF_HUB_OFFLINE":"1","TRANSFORMERS_OFFLINE":"1"}}
    compose=yaml.safe_dump({"services":{"main":service}},sort_keys=False)
    compose+="    deploy:\n      resources:\n        reservations:\n          devices: !reset []\n"
    (task/"environment/docker-compose.yaml").write_text(compose)
    job={"jobs_dir":str(run/"pier-jobs"),"job_name":"native-nop","n_attempts":1,
         "n_concurrent_trials":1,"retry":{"max_retries":0},"environment":{
             "type":"docker","force_build":False,"override_memory_mb":245760,
             "cpu_enforcement_policy":"ignore","memory_enforcement_policy":"ignore",
             "mounts":[{"type":"bind","source":volumes["gpt"]["shared_host_path"],
                        "target":"/models/target","read_only":True,"bind":{"create_host_path":False}}]
         },"agents":[{"name":"nop"}],"tasks":[{"path":str(task)}]}
    JobConfig.model_validate(job)
    config=run/"native-nop.json"
    config.write_text(json.dumps(job,indent=2)+"\n")
    return config

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("run",type=Path)
    parser.add_argument("devices",type=Path)
    args=parser.parse_args()
    print(prepare(args.run.resolve(),args.devices))
