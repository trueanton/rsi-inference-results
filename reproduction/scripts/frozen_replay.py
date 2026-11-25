"""Apply the frozen committed tree in a fresh Pier sandbox for verification."""
import os
from pathlib import Path
import re
from pier.agents.base import BaseAgent

class FrozenReplay(BaseAgent):
    @staticmethod
    def name():
        return "frozen-candidate-replay"
    def version(self):
        return "1"

    async def setup(self, environment):
        pass

    async def run(self, instruction, environment, context):
        archive=Path(os.environ["RSI_FROZEN_ARCHIVE"])
        state=(archive/"candidate-state.txt").read_text().splitlines()
        if len(state)!=4 or not all(re.fullmatch("[a-f0-9]{40}",x) for x in state):
            raise ValueError("Need clean recorded HEAD, base and both tree objects")
        head_tree,base_tree=state[2:]
        frozen=archive/"candidate.patch"
        if not frozen.is_file() or frozen.stat().st_size==0:
            raise ValueError("A replay requires a substantive frozen patch")
        before=await environment.exec("git -C /app/repo rev-parse inference_base^{tree}")
        if before.return_code or (before.stdout or "").strip()!=base_tree:
            raise ValueError("Fresh base has different source content")
        await environment.upload_file(frozen,"/tmp/rsi-frozen.patch")
        result=await environment.exec("cd /app/repo && git apply --index --binary /tmp/rsi-frozen.patch && git -c user.name='Frozen replay' -c user.email='replay@localhost' commit -qm 'Replay frozen candidate' && git rev-parse HEAD^{tree} && git status --porcelain",timeout_sec=300)
        if result.return_code or (result.stdout or "").strip()!=head_tree:
            raise ValueError("Reconstructed candidate differs from the archived tree")
        (self.logs_dir/"replayed-tree.txt").write_text(head_tree+"\n")
