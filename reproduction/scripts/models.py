#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
from datetime import datetime, timezone
from urllib.request import urlopen

for key in ("ALL_PROXY","all_proxy","HTTP_PROXY","http_proxy","HTTPS_PROXY","https_proxy","NO_PROXY","no_proxy"):
    os.environ.pop(key, None)
ROOT = Path("@BENCH_ROOT@/experiments")
SCRATCH = Path("@LOCAL_ROOT@")
MANIFEST = ROOT / "configs/models.json"
os.environ["HF_HOME"] = str(SCRATCH / "cache/huggingface")
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
from huggingface_hub import snapshot_download

PINS = {
    "qwen": ("Qwen/Qwen3.6-27B", "1cda14dd71a3f47115850eb790f416f165da1cb5", "Qwen3_5ForConditionalGeneration"),
    "gpt": ("openai/gpt-oss-120b", "b5c939de8f754692c1647ca79fbf85e8c1e70f8a", "GptOssForCausalLM"),
}

def now():
    return datetime.now(timezone.utc).isoformat()

def metadata(url):
    with urlopen(url, timeout=45) as response:
        return json.load(response)

def prepare():
    if MANIFEST.exists():
        return
    models = {}
    for key, (repo, sha, architecture) in PINS.items():
        api = metadata(f"https://huggingface.co/api/models/{repo}/revision/{sha}?blobs=true")
        assert api["sha"] == sha
        base = f"https://huggingface.co/{repo}/resolve/{sha}"
        index = metadata(f"{base}/model.safetensors.index.json")
        config = metadata(f"{base}/config.json")
        assert architecture in config["architectures"]
        shards = set(index["weight_map"].values())
        files = {}
        for item in api["siblings"]:
            name = item["rfilename"]
            if "/" in name:
                continue
            if name.endswith(".safetensors") and name not in shards:
                raise ValueError(f"Unindexed weight file {name}")
            files[name] = {"bytes": item["size"], "git_blob": item["blobId"]}
            if item.get("lfs"):
                files[name]["sha256"] = item["lfs"]["sha256"]
        if not shards <= files.keys():
            raise ValueError(f"Missing indexed files for {repo}")
        models[key] = dict(repo=repo, revision=sha, architecture=architecture,
            model_type=config["model_type"], quantization=config.get("quantization_config"),
            dtype=config.get("dtype", config.get("text_config",{}).get("dtype")),
            index_weight_bytes=int(index["metadata"]["total_size"]),
            indexed_shards=sorted(shards), files=files, expected_bytes=sum(v["bytes"] for v in files.values()),
            selection="All top-level files, including every indexed shard. Nested alternate representations omitted.",
            download_host="download host", destination=str(SCRATCH / "models" / repo.split("/")[1] / sha),
            intended_container_mount="/models/target", mount_mode="ro", observed_utc=now())
    with MANIFEST.open("x") as out:
        json.dump(models,out,indent=2)
        out.write("\n")

def transfer(key):
    entry=json.loads(MANIFEST.read_text())[key]
    assert entry["revision"] == PINS[key][1]
    dest=Path(entry["destination"])
    args=dict(repo_id=entry["repo"], revision=entry["revision"], local_dir=dest,
              allow_patterns=list(entry["files"]), max_workers=3)
    dry=snapshot_download(**args,dry_run=True)
    required=sum(item.file_size for item in dry if item.will_download)
    if shutil.disk_usage(SCRATCH).free < required:
        raise RuntimeError(f"Insufficient scratch for {required} remaining bytes")
    print(now(), key, "dry-run",len(dry),"files, remaining bytes",required,flush=True)
    snapshot_download(**args)
    verified={}
    for name, info in entry["files"].items():
        path=dest/name
        if not path.is_file() or path.stat().st_size != info["bytes"]:
            raise ValueError(f"Size mismatch at {path}")
        with path.open("rb") as stream:
            if "sha256" in info:
                digest=hashlib.file_digest(stream, "sha256").hexdigest()
                if digest != info["sha256"]:
                    raise ValueError(f"SHA256 mismatch for {name}")
            else:
                data=stream.read()
                git_hash=hashlib.sha1(b"blob "+str(len(data)).encode()+b"\x00"+data).hexdigest()
                if git_hash != info["git_blob"]:
                    raise ValueError(f"Git object mismatch for {name}")
                digest=hashlib.sha256(data).hexdigest()
        verified[name]=digest
    index=json.loads((dest/"model.safetensors.index.json").read_text())
    assert set(index["weight_map"].values()) == set(entry["indexed_shards"])
    assert entry["architecture"] in json.loads((dest/"config.json").read_text())["architectures"]
    assert json.loads((dest/"tokenizer_config.json").read_text())
    assert json.loads((dest/"tokenizer.json").read_text())
    report=dict(repo=entry["repo"],revision=entry["revision"],completed_utc=now(),
                directory=str(dest.resolve()),bytes=entry["expected_bytes"],sha256=verified)
    out=ROOT / "configs" / f"{key}-verified.json"
    tmp=out.with_suffix(".tmp")
    tmp.write_text(json.dumps(report,indent=2)+"\n")
    tmp.replace(out)
    print(now(),key,"verified", len(verified),"files",entry["expected_bytes"],"bytes",flush=True)

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("stage", choices=["manifest", *PINS])
    stage=parser.parse_args().stage
    if stage=="manifest":
        prepare()
    else:
        transfer(stage)
