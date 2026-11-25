"""Check the unchanged archived candidate in the fresh sandbox before Pier verifies it."""
import json
import os
from pathlib import Path
from pier.agents.base import BaseAgent

class FrozenReplay(BaseAgent):
    @staticmethod
    def name():
        return "verify-recorded-unchanged-tree"
    def version(self):
        return "1"
    async def setup(self, environment):
        pass
    async def run(self, instruction, environment, context):
        archive=Path(os.environ["RSI_FROZEN_ARCHIVE"])
        head,base,tree,base_tree=(archive/"candidate-state.txt").read_text().splitlines()
        if head!=base or tree!=base_tree or any((archive/n).read_bytes() for n in ("candidate.patch","uncommitted.patch")):
            raise ValueError("Archived candidate is not empty and clean")
        cmd="cd /app/repo && git rev-parse HEAD inference_base HEAD^{tree} inference_base^{tree} && git status --porcelain"
        result=await environment.exec(cmd,timeout_sec=90)
        state=(result.stdout or "").strip().splitlines()
        if result.return_code or len(state)!=4 or state[0]!=state[1] or state[2:]!=[tree,tree]:
            raise ValueError("Fresh candidate and baseline must reproduce the archived clean source")
        evidence=dict(solver_commit=head,solver_base_commit=base,fresh_commit=state[0],fresh_base_commit=state[1],
                      archived_tree=tree,fresh_tree=state[2],working_tree_clean=True)
        (self.logs_dir/"replayed-tree.json").write_text(json.dumps(evidence,indent=2)+"\n")
