#!/usr/bin/env python3
"""Create a separate operator-only GPT-OSS A100 port for Pier."""
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import tomllib
from pier.models.job.config import JobConfig

def prepare(run, inventory, mode):
    source=Path(__file__).with_name("prepare-nop.py")
    spec=importlib.util.spec_from_file_location("prepare_nop",source)
    nop=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(nop)
    target=nop.prepare(run,inventory)
    config=json.loads(target.read_text())
    task=Path(config["tasks"][0]["path"])
    exp=Path("@BENCH_ROOT@/experiments")
    setup=Path(__file__).parent/"setup"
    if not setup.is_dir():
        setup=exp/"patches/setup"
    subprocess.run(["patch","--batch","-d",str(task),"-p1","-i",str(setup/"gpt-a100-evaluator.patch")],check=True)
    compose=task/"environment/docker-compose.yaml"
    text=compose.read_text()
    marker="    environment:\n"
    if text.count(marker)!=1:
        raise ValueError("Unexpected compose environment")
    values=dict(tomllib.loads((task/"task.toml").read_text())["environment"]["env"])
    values.update(RSI_TARGET="gpt",INFB_DIAG_GPU_MEM_UTIL="0.95",INFB_GPU_MEMORY_UTILIZATION="0.95",
        INFB_CORRECTNESS_GPU_MEM_UTIL="0.95",VLLM_MEMORY_PROFILER_ESTIMATE_CUDAGRAPHS="1",
        INFB_CORRECTNESS_TP="2",TIKTOKEN_ENCODINGS_BASE="/runtime/encodings")
    compose.write_text(text.replace(marker,marker+"".join(f"      {k}: {json.dumps(str(v))}\n" for k,v in values.items())))
    exp=Path("@BENCH_ROOT@/experiments")
    public=task/"environment/scripts"
    subprocess.run(["patch","-d",str(public),"-p1","-i",str(setup/"gpt-public-correctness-memory.patch")],check=True)
    for src,dst in ((public/"run_correctness.py","/app/scripts/run_correctness.py"),
        (Path("@SHARED_ROOT@/runtime-assets/tiktoken"),"/runtime/encodings")):
        config["environment"]["mounts"].append(dict(type="bind",source=str(src),target=dst,read_only=True,bind=dict(create_host_path=False)))
    config["job_name"]="a100-port-"+mode
    if mode=="solver":
        config["agents"]=[dict(import_path="local_pier_solver:LocalPierSolver",model_name="openai/gpt-oss-120b")]
    elif mode=="replay":
        config["agents"]=[dict(import_path="frozen_replay:FrozenReplay")]
    JobConfig.model_validate(config)
    out=run/("a100-port-"+mode+".json")
    out.write_text(json.dumps(config,indent=2)+"\n")
    return out

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("run",type=Path)
    parser.add_argument("inventory",type=Path)
    parser.add_argument("mode",choices=["nop","solver","replay"])
    args=parser.parse_args()
    print(prepare(args.run.resolve(),args.inventory.resolve(),args.mode))
