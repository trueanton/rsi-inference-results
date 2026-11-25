#!/usr/bin/env python3
"""Host-side mini-SWE-agent. The only model tool executes in the fresh Pier sandbox."""
import json
import os
from pathlib import Path
import re
import sys

for key in ("ALL_PROXY","HTTP_PROXY","HTTPS_PROXY","NO_PROXY"):
    os.environ.pop(key,None)
    os.environ.pop(key.lower(),None)
os.environ["LITELLM_LOCAL_MODEL_COST_MAP"]="true"
os.environ["MSWEA_COST_TRACKING"]="ignore_errors"
os.environ["MSWEA_CONFIGURED"]="true"
os.environ["MSWEA_GLOBAL_CONFIG_DIR"]=str(Path(sys.argv[1])/"mini-config") if __name__=="__main__" else "/nonexistent"
os.environ["OPENAI_API_KEY"]="local-unix-socket"
import httpx
import litellm
import minisweagent
import yaml
from minisweagent.agents.default import DefaultAgent
from minisweagent.environments.docker import DockerEnvironment
from minisweagent.models.litellm_model import LitellmModel

class PierContainer(DockerEnvironment):
    def _start_container(self):
        cid = os.environ["RSI_SOLVER_CONTAINER_ID"]
        if not re.fullmatch("[0-9a-f]{12,64}",cid):
            raise ValueError("Invalid Pier main container ID")
        self.container_id = cid

    def cleanup(self):
        # Pier owns the sandbox through verification.
        pass

def main():
    run = Path(sys.argv[1])
    base = Path(minisweagent.__file__).parent / "config/mini.yaml"
    config = yaml.safe_load(base.read_text())
    # The local endpoint has a private Unix socket and no network interface.
    litellm.client_session = httpx.Client(transport=httpx.HTTPTransport(uds=os.environ["RSI_SOLVER_UDS"]),trust_env=False)
    kwargs = config["model"]["model_kwargs"]
    kwargs.update(api_base="http://localhost/v1",reasoning_effort="medium",temperature=0.6,
                  max_tokens=3072,timeout=240)
    model = LitellmModel(model_name="openai/gpt-oss-120b",cost_tracking="ignore_errors",**config["model"])
    env = PierContainer(image="pier-task",cwd="/app",interpreter=["bash","-c"],env=config["environment"].get("env",{}),
        executable=str(Path(__file__).with_name("solver-docker-exec.sh")),timeout=14400)
    agent_config = dict(config["agent"])
    agent_config.pop("mode",None)
    agent_config.update(cost_limit=0,wall_time_limit_seconds=30000,output_path=run/"mini-swe-agent.trajectory.json")
    # The public instruction and the operator's sanitized budget/setup note are the entire assignment.
    agent_config["instance_template"] = "{{task}}\n\nUse the bash tool for commands. Finish with echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT."
    agent = DefaultAgent(model,env,**agent_config)
    result = agent.run((run/"instruction.txt").read_text())
    (run/"exit.json").write_text(json.dumps(result,indent=2,default=str)+"\n")
    agent.save(agent_config["output_path"])

if __name__=="__main__":
    main()
